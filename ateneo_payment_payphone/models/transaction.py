# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import requests


class payment_transaction(models.Model):
    _inherit = "payment.transaction"

    url_payphone = fields.Char(string="Url Payphone")
    clientTransactionId_payphone = fields.Char(string="clientTransactionId")

    @api.model
    def _payphone_form_get_tx_from_data(self, data):
        reference = data.get("clientTransactionId", False)
        tx = self.search([('clientTransactionId_payphone', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('Payphone: received data for reference %s') % (
                reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            raise ValidationError(error_msg)

        return tx

    def _payphone_form_validate(self, data):
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer %s' % self.acquirer_id.token_payphone}
        transactionId, clientTransactionId = data.get("id"), data.get(
            "clientTransactionId")
        json_data = {"id": transactionId, "clientTxId": clientTransactionId}
        if transactionId != "0":
            res = requests.post(
                "%s/api/button/confirm" % (self.acquirer_id.url_payphone),
                headers=headers, json=json_data)
            if res.status_code != 200:
                return False
            status = res.json()["statusCode"]
        else:
            status = 2

        if status == 3:
            tx_state = "done"
        elif status == 1:
            tx_state = "pending"
        elif status == 2:
            tx_state = "cancel"

        self.write({
            "state": tx_state,
            "acquirer_reference": transactionId,
        })
        return True
