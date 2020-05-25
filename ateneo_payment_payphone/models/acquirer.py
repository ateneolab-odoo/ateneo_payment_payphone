# -*- coding: utf-8 -*-

from odoo import models, fields, api
from decimal import Decimal
import random, requests, string


class paymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[('payphone', 'PayPhone')])
    url_payphone = fields.Char(string="Url Payphone")
    token_payphone = fields.Text(string="Token Payphone")

    def format_amount(self, value):
        TWOPLACES = Decimal(10) ** -2
        return int(Decimal(value).quantize(TWOPLACES) * 100)

    @api.model
    def payphone_payment_link(self, values):
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer %s' % self.token_payphone}
        payment_link, payment_id = "", False

        reference = "%s-(%s)" % (
            values.get("reference", False), values.get("partner", False).name)
        clientTransactionId = "%s-%s" % (values.get("reference", False),
                                         ''.join(
                                             random.choice(string.digits) for _
                                             in range(6)))
        data = {
            "amountWithoutTax": self.format_amount(values.get("amount", False)),
            "amount": self.format_amount(values.get("amount", False)),
            "currency": values.get("currency", False).name,
            "clientTransactionId": clientTransactionId,
            "responseUrl": "%s/payment/payphone/feedback" % (
                self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')),
            "cancellationUrl": "%s/payment/payphone/cancel" % (
                self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')),
            "reference": reference[:50],
        }
        response = requests.post("%s/api/button/Prepare" % self.url_payphone,
                                 headers=headers, json=data)
        if response.json().get("paymentId", False) and response.json().get(
                "payWithPayPhone", False):
            payment_id = response.json()["paymentId"]
            payment_link = response.json()["payWithPayPhone"]
        return payment_id, payment_link, clientTransactionId

    @api.multi
    def payphone_form_generate_values(self, values):
        tx_values = dict(values)
        tx_id = self._context.get("tx_id", False)
        if tx_id:
            values.update({"tx_id": tx_id})
            payment_id, payment_link, clientTransactionId = self.payphone_payment_link(
                values)
            tx_id.write({"url_payphone": payment_link,
                         "clientTransactionId_payphone": clientTransactionId})
            tx_values.update({
                'paymentId': payment_id,
            })
        return tx_values

    @api.multi
    def payphone_get_form_action_url(self):
        tx_id = self._context.get("tx_id", False)
        if tx_id:
            return tx_id.url_payphone
        else:
            return ""
