from datetime import datetime
from itertools import groupby

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends_context("force_company")
    def _compute_due_amount(self):
        for rec in self:
            rec.due_amount = self.compute_due_amount_to_date().get(rec.id, 0.0)

    def compute_due_amount_to_date(self, to_date=False):
        if not to_date:
            to_date = datetime.today().strftime(DF)
        res = {}
        sorted_mvl = self.partner_due_lines(to_date)
        for key, vals in groupby(sorted_mvl, key=lambda x: x.partner_id.id):
            res[key] = sum([rec.amount_residual for rec in vals])
        return res

    def partner_due_lines(self, to_date):
        sorted_mvl = (
            self.env["account.move.line"]
            .search(
                [
                    ("move_id.state", "=", "posted"),
                    ("partner_id", "in", self.ids),
                    ("account_id.user_type_id.type", "=", "receivable"),
                    ("reconciled", "=", False),
                    ("date_maturity", "<=", to_date),
                    ("display_type", "not in", ("line_section", "line_note")),
                ]
            )
            .sorted(key=lambda x: x.partner_id.id)
        )
        return sorted_mvl

    def action_view_partner_due_invoices(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        move_ids = self.partner_due_lines(datetime.today()).mapped("move_id").ids
        action["domain"] = [
            ("id", "in", move_ids),
        ]
        action["context"] = {
            "default_type": "out_invoice",
            "type": "out_invoice",
            "journal_type": "sale",
            "search_default_unpaid": 1,
        }
        return action

    @api.model
    def get_violations(self):
        # archive all history records for partners who don't have credit policy
        self.search([("credit_policy_id", "=", False)]).reset_violations_history()
        self.search([("credit_policy_id", "!=", False)])._get_partner_violations()

    def _get_partner_violations(self):
        partners_not_exceeded = self.browse()
        for partner in self:
            # if there is no violated_limit archive all history records for this partner
            # if there is violated_limit and not history record for this partner
            # with with this limit create history record and run actions
            # if there is a history record do nothing
            violated_limit = self.credit_policy_id.get_violate(partner)
            if not violated_limit:
                partners_not_exceeded |= partner
            if violated_limit:
                violation_history = self.env[
                    "customer.credit.policy.limit.history"
                ].search(
                    [
                        ("partner_id", "=", partner.id),
                        ("limit_id", "=", violated_limit.id),
                    ]
                )
                if not violation_history:
                    partner.violated_limit_id = violated_limit.id
                    self.env["customer.credit.policy.limit.history"].create(
                        {"partner_id": partner.id, "limit_id": violated_limit.id}
                    )
                    violated_limit.do_limit_acions(partner)
            partners_not_exceeded.reset_violations_history()

    def reset_violations_history(self):
        self.write({"violated_limit_id": False})
        self.env["customer.credit.policy.limit.history"].search(
            [("partner_id", "in", self.ids)]
        ).write({"active": False})

    due_amount = fields.Monetary(
        compute="_compute_due_amount", string="Due Amount As of Today"
    )
    credit_policy_id = fields.Many2one(
        comodel_name="customer.credit.policy", string="Credit Policy"
    )
    violated_limit_id = fields.Many2one(
        comodel_name="customer.credit.policy.limit",
        string="Violated Limit",
        help="Specify if the customer violate any credit limt.",
    )

    def write(self, values):
        credit_policy_id = False

        if "credit_policy_id" in values:
            credit_policy_id = values["credit_policy_id"]

        res = super(ResPartner, self).write(values)

        if credit_policy_id:
            if credit_policy_id:
                self._get_partner_violations()
            if not credit_policy_id:
                self.reset_violations_history()
        return res
