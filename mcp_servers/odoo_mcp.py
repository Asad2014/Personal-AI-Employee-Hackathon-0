"""Odoo MCP Server — exposes accounting and CRM tools via Odoo JSON-RPC API.

Connects to a local Odoo 19 instance (Docker) and provides tools for:
- Invoice management (create, list, get)
- Contact/partner management (create, list, search)
- Account summary and financial reporting
- CEO Briefing data aggregation
"""

import asyncio
import json
import os
import xmlrpc.client
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

server = Server("odoo-accounting")

# ---------------------------------------------------------------------------
# Odoo connection helpers
# ---------------------------------------------------------------------------

ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'odoo')
ODOO_USER = os.environ.get('ODOO_USER', 'admin')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'admin')


def _get_uid() -> int:
    """Authenticate and return the user ID."""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ConnectionError("Odoo authentication failed — check ODOO_DB, ODOO_USER, ODOO_PASSWORD")
    return uid


def _get_models():
    """Return the Odoo models XML-RPC proxy."""
    return xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')


def _execute(model: str, method: str, *args, **kwargs):
    """Execute an Odoo RPC call."""
    uid = _get_uid()
    models = _get_models()
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, *args, **kwargs)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="create_invoice",
        description=(
            "Create a new customer invoice in Odoo. Returns the invoice ID. "
            "IMPORTANT: Invoices over $100 require human approval per Company Handbook."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "partner_name": {
                    "type": "string",
                    "description": "Customer/partner name (will search or create)",
                },
                "invoice_lines": {
                    "type": "array",
                    "description": "List of invoice line items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "description": "Line item description"},
                            "quantity": {"type": "number", "description": "Quantity (default 1)", "default": 1},
                            "price_unit": {"type": "number", "description": "Unit price"},
                        },
                        "required": ["description", "price_unit"],
                    },
                },
                "reference": {
                    "type": "string",
                    "description": "Invoice reference/PO number (optional)",
                },
            },
            "required": ["partner_name", "invoice_lines"],
        },
    ),
    Tool(
        name="list_invoices",
        description="List recent invoices from Odoo with status and amounts.",
        inputSchema={
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Filter by state: draft, posted, cancel (optional, default: all)",
                    "enum": ["draft", "posted", "cancel"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Max invoices to return (default 20)",
                    "default": 20,
                },
                "days": {
                    "type": "integer",
                    "description": "Only show invoices from the last N days (default 30)",
                    "default": 30,
                },
            },
        },
    ),
    Tool(
        name="get_invoice",
        description="Get details of a specific invoice by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "The Odoo invoice ID",
                },
            },
            "required": ["invoice_id"],
        },
    ),
    Tool(
        name="create_contact",
        description="Create a new contact/partner in Odoo CRM.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Contact full name"},
                "email": {"type": "string", "description": "Email address"},
                "phone": {"type": "string", "description": "Phone number (optional)"},
                "company": {"type": "string", "description": "Company name (optional)"},
                "is_company": {"type": "boolean", "description": "Is this a company (true) or person (false)", "default": False},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="list_contacts",
        description="List contacts/partners from Odoo.",
        inputSchema={
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Search term to filter contacts by name or email (optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max contacts to return (default 20)",
                    "default": 20,
                },
            },
        },
    ),
    Tool(
        name="get_account_summary",
        description=(
            "Get a financial summary from Odoo: total revenue, outstanding invoices, "
            "recent payments. Perfect for CEO Briefings and weekly audits."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "period_days": {
                    "type": "integer",
                    "description": "Summary period in days (default 30)",
                    "default": 30,
                },
            },
        },
    ),
    Tool(
        name="get_ceo_briefing_data",
        description=(
            "Aggregate all data needed for a CEO Briefing: revenue, outstanding invoices, "
            "new contacts, overdue payments, and key metrics over a specified period."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "period_days": {
                    "type": "integer",
                    "description": "Briefing period in days (default 7 for weekly)",
                    "default": 7,
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _find_or_create_partner(name: str, email: str = '', phone: str = '') -> int:
    """Search for an existing partner by name/email, or create a new one."""
    domain = ['|', ('name', 'ilike', name)]
    if email:
        domain.append(('email', '=', email))
    else:
        domain.append(('name', 'ilike', name))

    partner_ids = _execute('res.partner', 'search', [domain], {'limit': 1})
    if partner_ids:
        return partner_ids[0]

    # Create new partner
    vals = {'name': name}
    if email:
        vals['email'] = email
    if phone:
        vals['phone'] = phone
    return _execute('res.partner', 'create', [vals])


async def handle_create_invoice(arguments: dict) -> str:
    """Create a customer invoice in Odoo."""
    partner_name = arguments['partner_name']
    lines = arguments['invoice_lines']
    reference = arguments.get('reference', '')

    partner_id = _find_or_create_partner(partner_name)

    invoice_lines = []
    for line in lines:
        invoice_lines.append((0, 0, {
            'name': line['description'],
            'quantity': line.get('quantity', 1),
            'price_unit': line['price_unit'],
        }))

    vals = {
        'move_type': 'out_invoice',
        'partner_id': partner_id,
        'invoice_line_ids': invoice_lines,
    }
    if reference:
        vals['ref'] = reference

    invoice_id = _execute('account.move', 'create', [vals])

    # Read back the invoice to get the total
    invoice = _execute('account.move', 'read', [invoice_id], {
        'fields': ['name', 'amount_total', 'state', 'partner_id'],
    })
    inv = invoice[0] if invoice else {}

    return json.dumps({
        "status": "created",
        "invoice_id": invoice_id,
        "number": inv.get('name', ''),
        "amount_total": inv.get('amount_total', 0),
        "state": inv.get('state', 'draft'),
        "partner": inv.get('partner_id', [0, ''])[1] if isinstance(inv.get('partner_id'), (list, tuple)) else str(inv.get('partner_id', '')),
    })


async def handle_list_invoices(arguments: dict) -> str:
    """List recent invoices."""
    limit = arguments.get('limit', 20)
    days = arguments.get('days', 30)
    state = arguments.get('state')

    date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    domain = [
        ('move_type', '=', 'out_invoice'),
        ('invoice_date', '>=', date_from),
    ]
    if state:
        domain.append(('state', '=', state))

    invoice_ids = _execute('account.move', 'search', [domain], {
        'limit': limit,
        'order': 'invoice_date desc',
    })

    if not invoice_ids:
        return json.dumps({"invoices": [], "count": 0})

    invoices = _execute('account.move', 'read', [invoice_ids], {
        'fields': ['name', 'partner_id', 'invoice_date', 'amount_total',
                    'amount_residual', 'state', 'ref'],
    })

    result = []
    for inv in invoices:
        partner = inv.get('partner_id', [0, ''])
        result.append({
            'id': inv['id'],
            'number': inv.get('name', ''),
            'partner': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
            'date': inv.get('invoice_date', ''),
            'total': inv.get('amount_total', 0),
            'outstanding': inv.get('amount_residual', 0),
            'state': inv.get('state', ''),
            'reference': inv.get('ref', ''),
        })

    return json.dumps({"invoices": result, "count": len(result)})


async def handle_get_invoice(arguments: dict) -> str:
    """Get a specific invoice."""
    invoice_id = arguments['invoice_id']
    invoices = _execute('account.move', 'read', [[invoice_id]], {
        'fields': ['name', 'partner_id', 'invoice_date', 'invoice_date_due',
                    'amount_total', 'amount_residual', 'state', 'ref',
                    'invoice_line_ids'],
    })

    if not invoices:
        return json.dumps({"error": f"Invoice {invoice_id} not found"})

    inv = invoices[0]

    # Get line items
    line_ids = inv.get('invoice_line_ids', [])
    lines = []
    if line_ids:
        line_data = _execute('account.move.line', 'read', [line_ids], {
            'fields': ['name', 'quantity', 'price_unit', 'price_subtotal'],
        })
        for ld in line_data:
            if ld.get('price_unit', 0) != 0:
                lines.append({
                    'description': ld.get('name', ''),
                    'quantity': ld.get('quantity', 0),
                    'unit_price': ld.get('price_unit', 0),
                    'subtotal': ld.get('price_subtotal', 0),
                })

    partner = inv.get('partner_id', [0, ''])
    return json.dumps({
        'id': inv['id'],
        'number': inv.get('name', ''),
        'partner': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
        'date': inv.get('invoice_date', ''),
        'due_date': inv.get('invoice_date_due', ''),
        'total': inv.get('amount_total', 0),
        'outstanding': inv.get('amount_residual', 0),
        'state': inv.get('state', ''),
        'reference': inv.get('ref', ''),
        'lines': lines,
    })


async def handle_create_contact(arguments: dict) -> str:
    """Create a new contact in Odoo."""
    vals = {'name': arguments['name']}
    if arguments.get('email'):
        vals['email'] = arguments['email']
    if arguments.get('phone'):
        vals['phone'] = arguments['phone']
    if arguments.get('company'):
        vals['parent_id'] = _find_or_create_partner(arguments['company'])
    if arguments.get('is_company'):
        vals['is_company'] = True

    partner_id = _execute('res.partner', 'create', [vals])
    return json.dumps({"status": "created", "contact_id": partner_id, "name": arguments['name']})


async def handle_list_contacts(arguments: dict) -> str:
    """List contacts from Odoo."""
    limit = arguments.get('limit', 20)
    search = arguments.get('search', '')

    domain = []
    if search:
        domain = ['|', ('name', 'ilike', search), ('email', 'ilike', search)]

    partner_ids = _execute('res.partner', 'search', [domain], {
        'limit': limit,
        'order': 'name',
    })

    if not partner_ids:
        return json.dumps({"contacts": [], "count": 0})

    partners = _execute('res.partner', 'read', [partner_ids], {
        'fields': ['name', 'email', 'phone', 'is_company', 'city', 'country_id'],
    })

    contacts = []
    for p in partners:
        country = p.get('country_id', [0, ''])
        contacts.append({
            'id': p['id'],
            'name': p.get('name', ''),
            'email': p.get('email', ''),
            'phone': p.get('phone', ''),
            'is_company': p.get('is_company', False),
            'city': p.get('city', ''),
            'country': country[1] if isinstance(country, (list, tuple)) else str(country),
        })

    return json.dumps({"contacts": contacts, "count": len(contacts)})


async def handle_get_account_summary(arguments: dict) -> str:
    """Get financial summary."""
    days = arguments.get('period_days', 30)
    date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Total revenue (posted invoices)
    invoice_ids = _execute('account.move', 'search', [[
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', date_from),
    ]])

    total_revenue = 0
    total_outstanding = 0
    invoice_count = 0

    if invoice_ids:
        invoices = _execute('account.move', 'read', [invoice_ids], {
            'fields': ['amount_total', 'amount_residual'],
        })
        for inv in invoices:
            total_revenue += inv.get('amount_total', 0)
            total_outstanding += inv.get('amount_residual', 0)
            invoice_count += 1

    # Draft invoices
    draft_ids = _execute('account.move', 'search', [[
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'draft'),
    ]])

    # Overdue invoices
    today = datetime.now().strftime('%Y-%m-%d')
    overdue_ids = _execute('account.move', 'search', [[
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('amount_residual', '>', 0),
        ('invoice_date_due', '<', today),
    ]])

    overdue_total = 0
    if overdue_ids:
        overdue_invoices = _execute('account.move', 'read', [overdue_ids], {
            'fields': ['amount_residual'],
        })
        overdue_total = sum(inv.get('amount_residual', 0) for inv in overdue_invoices)

    return json.dumps({
        "period_days": days,
        "total_revenue": round(total_revenue, 2),
        "total_outstanding": round(total_outstanding, 2),
        "invoices_posted": invoice_count,
        "invoices_draft": len(draft_ids),
        "overdue_invoices": len(overdue_ids),
        "overdue_amount": round(overdue_total, 2),
        "collected": round(total_revenue - total_outstanding, 2),
    })


async def handle_get_ceo_briefing_data(arguments: dict) -> str:
    """Aggregate data for CEO Briefing."""
    days = arguments.get('period_days', 7)
    date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')

    # Revenue data
    posted_ids = _execute('account.move', 'search', [[
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', date_from),
    ]])

    revenue_this_period = 0
    invoices_detail = []
    if posted_ids:
        invoices = _execute('account.move', 'read', [posted_ids], {
            'fields': ['name', 'partner_id', 'amount_total', 'amount_residual', 'invoice_date'],
        })
        for inv in invoices:
            revenue_this_period += inv.get('amount_total', 0)
            partner = inv.get('partner_id', [0, ''])
            invoices_detail.append({
                'number': inv.get('name', ''),
                'partner': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
                'amount': inv.get('amount_total', 0),
                'outstanding': inv.get('amount_residual', 0),
                'date': inv.get('invoice_date', ''),
            })

    # Overdue invoices
    overdue_ids = _execute('account.move', 'search', [[
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('amount_residual', '>', 0),
        ('invoice_date_due', '<', today),
    ]])

    overdue_detail = []
    overdue_total = 0
    if overdue_ids:
        overdue_invs = _execute('account.move', 'read', [overdue_ids], {
            'fields': ['name', 'partner_id', 'amount_residual', 'invoice_date_due'],
        })
        for inv in overdue_invs:
            overdue_total += inv.get('amount_residual', 0)
            partner = inv.get('partner_id', [0, ''])
            overdue_detail.append({
                'number': inv.get('name', ''),
                'partner': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
                'outstanding': inv.get('amount_residual', 0),
                'due_date': inv.get('invoice_date_due', ''),
            })

    # New contacts this period
    new_partner_ids = _execute('res.partner', 'search', [[
        ('create_date', '>=', date_from),
        ('is_company', '=', False),
        ('customer_rank', '>', 0),
    ]])

    new_contacts = []
    if new_partner_ids:
        partners = _execute('res.partner', 'read', [new_partner_ids], {
            'fields': ['name', 'email', 'create_date'],
        })
        for p in partners:
            new_contacts.append({
                'name': p.get('name', ''),
                'email': p.get('email', ''),
                'created': p.get('create_date', ''),
            })

    # Total outstanding (all time)
    all_outstanding_ids = _execute('account.move', 'search', [[
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('amount_residual', '>', 0),
    ]])
    total_outstanding = 0
    if all_outstanding_ids:
        all_outstanding = _execute('account.move', 'read', [all_outstanding_ids], {
            'fields': ['amount_residual'],
        })
        total_outstanding = sum(inv.get('amount_residual', 0) for inv in all_outstanding)

    return json.dumps({
        "period_days": days,
        "period_start": date_from,
        "period_end": today,
        "revenue": {
            "total": round(revenue_this_period, 2),
            "invoice_count": len(posted_ids),
            "invoices": invoices_detail,
        },
        "outstanding": {
            "total": round(total_outstanding, 2),
        },
        "overdue": {
            "count": len(overdue_ids),
            "total": round(overdue_total, 2),
            "invoices": overdue_detail,
        },
        "new_contacts": {
            "count": len(new_contacts),
            "contacts": new_contacts,
        },
    })


# ---------------------------------------------------------------------------
# MCP protocol handlers
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "create_invoice": handle_create_invoice,
        "list_invoices": handle_list_invoices,
        "get_invoice": handle_get_invoice,
        "create_contact": handle_create_contact,
        "list_contacts": handle_list_contacts,
        "get_account_summary": handle_get_account_summary,
        "get_ceo_briefing_data": handle_get_ceo_briefing_data,
    }

    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg:
            error_msg = f"Cannot connect to Odoo at {ODOO_URL} — is the Docker container running? (docker compose up -d)"
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
