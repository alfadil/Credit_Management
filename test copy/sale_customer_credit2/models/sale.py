from odoo import _, api, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains("partner_id")
    def _check_partner_id(self):
        for order in self:
            if (
                order.partner_id.violated_limit_id
                and order.partner_id.violated_limit_id.block_customer
            ):
                raise ValidationError(
                    _(
                        "Transactions with %s are BLOCKED accouring to Credit Policy"
                        % (order.partner_id.name,)
                    )
                )
