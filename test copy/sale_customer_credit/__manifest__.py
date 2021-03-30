{
    "name": "Customer Credit Policy",
    "summary": """Customer Credit Policy""",
    "author": "Alfadil Mustafa",
    "category": "Sales",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["sale_management", "partner_statement"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/customer_credit_policy_views.xml",
        "data/mail_template_data.xml",
        "data/ir_cron_data.xml",
    ],
}
