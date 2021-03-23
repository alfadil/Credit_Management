from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class CustomerCreditPolicy(models.Model):
    _name = "customer.credit.policy"
    _description = "Customer's Credit Policy"

    name = fields.Char(string="Name", required=True)
    limits_ids = fields.One2many(
        comodel_name="customer.credit.policy.limit",
        inverse_name="policy_id",
        string="Limts",
    )

    def get_violate(self, partner):
        today = datetime.today()
        for limit_record in self.limits_ids.sorted(
            key=lambda limit_rec: (limit_rec.limit, limit_rec.effect_after_days),
            reverse=True,
        ):
            limit_date = today - relativedelta(days=limit_record.effect_after_days)
            due_amount = partner.compute_due_amount_to_date(
                limit_date.strftime(DF)
            ).get(partner.id, 0.0)
            if due_amount >= limit_record.limit:
                return limit_record
        return False


class CustomerCreditPolicyLimit(models.Model):
    _name = "customer.credit.policy.limit"
    _description = "Customer's Credit Policy Limit"

    name = fields.Char(string="Name", required=True)
    policy_id = fields.Many2one(
        comodel_name="customer.credit.policy", string="Credit Policy"
    )

    limit = fields.Float(string="Limit")
    effect_after_days = fields.Integer(
        default=1, help="The limit actions effect after (in days)."
    )
    notify_responsible = fields.Boolean(string="Notify Responsible")
    send_mail = fields.Boolean(string="Send Mail")
    block_customer = fields.Boolean(string="Block Customer")
    responsible_id = fields.Many2one(comodel_name="res.users", string="Responsible")
    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type", string="Responsible Action"
    )
    activity_summary = fields.Char("Summary")
    activity_note = fields.Html("Note")
    template_id = fields.Many2one(
        "mail.template",
        "Use template",
        domain="[('model', '=', 'res.partner')]",
        default=lambda self: self.env.ref(
            "sale_customer_credit.email_template_partner_outstanding_invoices"
        ),
    )

    def do_limit_acions(self, partner):
        if self.send_mail and self.template_id:
            self.template_id.send_mail(
                partner.id, force_send=False, raise_exception=False
            )
        if self.notify_responsible and self.responsible_id:
            vals = {
                "summary": self.activity_summary or "",
                "note": self.activity_note or "",
                "activity_type_id": self.activity_type_id.id,
                "user_id": self.responsible_id.id,
            }
            partner.activity_schedule(**vals)


class CustomerCreditPolicyLimitHistory(models.Model):
    _name = "customer.credit.policy.limit.history"
    _description = "Customer's Credit Policy Limit History"

    partner_id = fields.Many2one(comodel_name="res.partner", string="Linked Partner",)
    limit_id = fields.Many2one(
        comodel_name="customer.credit.policy.limit", string="Credit Limit",
    )
    active = fields.Boolean(string="Active", default=True)
