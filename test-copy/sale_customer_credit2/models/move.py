from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("partner_id")
    def _check_partner_id(self):
        for mv in self:
            if (
                mv.type == "out_invoice"
                and mv.partner_id.violated_limit_id
                and mv.partner_id.violated_limit_id.block_customer
            ):
                raise ValidationError(
                    _(
                        "Transactions with %s are BLOCKED accouring to Credit Policy"
                        % (mv.partner_id.name,)
                    )
                )
