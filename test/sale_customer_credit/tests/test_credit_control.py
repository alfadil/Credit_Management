from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCreditControl(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.payment_method_manual_in = cls.env.ref(
            "account.account_payment_method_manual_in"
        )

        cls.product_line_vals_1 = {
            "name": cls.product_a.name,
            "product_id": cls.product_a.id,
            "account_id": cls.product_a.property_account_income_id.id,
            "partner_id": cls.partner_a.id,
            "product_uom_id": cls.product_a.uom_id.id,
            "quantity": 1.0,
            "discount": 0.0,
            "price_unit": 1000.0,
            "price_subtotal": 1000.0,
            "price_total": 1150.0,
            "tax_ids": cls.product_a.taxes_id.ids,
            "tax_line_id": False,
            "currency_id": cls.currency_data["currency"].id,
            "amount_currency": 0.0,
            "debit": 0.0,
            "credit": 1000.0,
            "tax_exigible": True,
        }
        cls.product_line_vals_2 = {
            "name": cls.product_b.name,
            "product_id": cls.product_b.id,
            "account_id": cls.product_b.property_account_income_id.id,
            "partner_id": cls.partner_a.id,
            "product_uom_id": cls.product_b.uom_id.id,
            "quantity": 1.0,
            "discount": 0.0,
            "price_unit": 200.0,
            "price_subtotal": 200.0,
            "price_total": 260.0,
            "tax_ids": cls.product_b.taxes_id.ids,
            "tax_line_id": False,
            "currency_id": cls.currency_data["currency"].id,
            "amount_currency": 0.0,
            "debit": 0.0,
            "credit": 200.0,
            "tax_exigible": True,
        }

        before_thirty_days = fields.Date.today() - relativedelta(days=30)
        before_five_days = fields.Date.today() - relativedelta(days=5)
        cls.move_1 = cls.env["account.move"].create(
            {
                "type": "out_invoice",
                "partner_id": cls.partner_a.id,
                "invoice_date": before_thirty_days.strftime(DF),
                "currency_id": cls.currency_data["currency"].id,
                "invoice_payment_term_id": cls.pay_terms_a.id,
                "invoice_line_ids": [
                    (0, None, cls.product_line_vals_1),
                    (0, None, cls.product_line_vals_2),
                ],
            }
        )

        cls.move_2 = cls.env["account.move"].create(
            {
                "type": "out_invoice",
                "partner_id": cls.partner_a.id,
                "invoice_date": before_five_days.strftime(DF),
                "currency_id": cls.currency_data["currency"].id,
                "invoice_payment_term_id": cls.pay_terms_a.id,
                "invoice_line_ids": [
                    (0, None, cls.product_line_vals_2),
                    (0, None, cls.product_line_vals_2),
                ],
            }
        )

        cls.policy_limit_a_vals = {
            "name": "Limit a",
            "limit": 250,
            "effect_after_days": 10,
            "block_customer": True,
        }

        cls.policy_limit_b_vals = {
            "name": "Limit b",
            "limit": 250,
            "effect_after_days": 5,
            "send_mail": True,
            "template_id": cls.env.ref(
                "sale_customer_credit.email_template_partner_outstanding_invoices"
            ).id,
        }

        cls.policy_limit_c_vals = {
            "name": "Limit c",
            "limit": 200,
            "effect_after_days": 2,
            "notify_responsible": True,
            "responsible_id": cls.env.user.id,
            "activity_type_id": cls.env.ref("mail.mail_activity_data_meeting").id,
            "activity_summary": "test summary",
        }

    # TEST 01: partner have late payments that exceeded the one limit
    def test_assign_policy_exceeded_one_limit(self):
        policy_1 = self.env["customer.credit.policy"].create({"name": "policy 1"})
        limit_a_vals = self.policy_limit_a_vals.copy()
        limit_a_vals["policy_id"] = policy_1.id

        limit_b_vals = self.policy_limit_b_vals.copy()
        limit_b_vals["policy_id"] = policy_1.id

        self.env["customer.credit.policy.limit"].create(limit_a_vals)
        limit_b = self.env["customer.credit.policy.limit"].create(limit_b_vals)

        self.move_2.post()
        self.partner_a.credit_policy_id = policy_1.id
        self.assertEqual(self.partner_a.violated_limit_id.id, limit_b.id)
        histories_ids = self.env["customer.credit.policy.limit.history"].search(
            [("partner_id", "=", self.partner_a.id), ("limit_id", "=", limit_b.id)]
        )
        self.assertEqual(len(histories_ids), 1)

    # TEST 02: 2 limits with different effect_after_days
    def test_assign_policy_exceeded_multi_limits(self):
        limit_a_25_days = self.policy_limit_a_vals.copy()
        limit_a_25_days["effect_after_days"] = 25
        limit_a_25_days["name"] = "25 days limit"
        policy_1 = self.env["customer.credit.policy"].create(
            {
                "name": "policy 1",
                "limits_ids": [
                    (0, None, self.policy_limit_a_vals),
                    (0, None, self.policy_limit_b_vals),
                    (0, None, limit_a_25_days),
                ],
            }
        )
        self.move_1.post()
        self.partner_a.credit_policy_id = policy_1.id
        self.assertEqual(self.partner_a.violated_limit_id.name, "25 days limit")

        # test the customer is blocked
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["account.move"].create(
                {
                    "type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "currency_id": self.currency_data["currency"].id,
                    "invoice_payment_term_id": self.pay_terms_a.id,
                    "invoice_line_ids": [(0, None, self.product_line_vals_2)],
                }
            )

        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["sale.order"].with_context(tracking_disable=True).create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                }
            )

    # TEST 03: re-check partner limit after payment
    def test_assign_policy_after_payment(self):
        policy_1 = self.env["customer.credit.policy"].create(
            {
                "name": "policy 1",
                "limits_ids": [
                    (0, None, self.policy_limit_a_vals),
                    (0, None, self.policy_limit_b_vals),
                    (0, None, self.policy_limit_c_vals),
                ],
            }
        )

        self.move_2.post()
        self.partner_a.credit_policy_id = policy_1.id
        histories_ids = self.env["customer.credit.policy.limit.history"].search(
            [("partner_id", "=", self.partner_a.id), ("limit_id.name", "=", "Limit b")]
        )
        self.assertEqual(len(histories_ids), 1)

        # make a partial payment
        payment_register = Form(
            self.env["account.payment"].with_context(
                active_model="account.move", active_ids=self.move_2.ids
            )
        )
        payment_register.payment_date = fields.Date.today().strftime(DF)
        payment_register.journal_id = self.env["account.journal"].create(
            {"name": "Bank", "type": "bank", "code": "BNK-test"}
        )
        payment_register.payment_method_id = self.payment_method_manual_in
        payment_register.currency_id = self.currency_data["currency"]
        payment_register.amount = 60
        payment = payment_register.save()
        payment.post()
        self.partner_a._get_partner_violations()
        self.assertEqual(self.partner_a.violated_limit_id.name, "Limit c")
