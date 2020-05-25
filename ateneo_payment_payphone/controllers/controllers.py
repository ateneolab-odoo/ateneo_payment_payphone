# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo.tools.translate import _
import werkzeug


class WebsiteSale(WebsiteSale):

    @http.route(['/shop/payment/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id, tx_type='form', token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        Transaction = request.env['payment.transaction'].sudo()

        # In case the route is called directly from the JS (as done in Stripe payment method)
        so_id = kwargs.get('so_id')
        so_token = kwargs.get('so_token')
        if so_id and so_token:
            order = request.env['sale.order'].sudo().search([('id', '=', so_id), ('access_token', '=', so_token)])
        elif so_id:
            order = request.env['sale.order'].search([('id', '=', so_id)])
        else:
            order = request.website.sale_get_order()
        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout")

        assert order.partner_id.id != request.website.partner_id.id

        # find an already existing transaction
        tx = request.website.sale_get_transaction()
        if tx:
            if tx.sale_order_id.id != order.id or tx.state in ['error', 'cancel'] or tx.acquirer_id.id != acquirer_id:
                tx = False
            elif token and tx.payment_token_id and token != tx.payment_token_id.id:
                # new or distinct token
                tx = False
            elif tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.write(dict(Transaction.on_change_partner_id(order.partner_id.id).get('value', {}),
                              amount=order.amount_total, type=tx_type))
        if not tx:
            tx_values = {
                'acquirer_id': acquirer_id,
                'type': tx_type,
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': Transaction.get_next_reference(order.name),
                'sale_order_id': order.id,
            }
            if token and request.env['payment.token'].sudo().browse(int(token)).partner_id == order.partner_id:
                tx_values['payment_token_id'] = token

            tx = Transaction.create(tx_values)
            request.session['sale_transaction_id'] = tx.id

        # update quotation
        order.write({
            'payment_acquirer_id': acquirer_id,
            'payment_tx_id': request.session['sale_transaction_id']
        })
        if token:
            return request.env.ref('website_sale.payment_token_form').render(dict(tx=tx), engine='ir.qweb')

        return tx.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=_('Pay Now'),
                                           tx_id=tx).sudo().render(
            tx.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values={
                'return_url': '/shop/payment/validate',
                'partner_id': order.partner_shipping_id.id or order.partner_invoice_id.id,
                'billing_partner_id': order.partner_invoice_id.id,
            },
        )

class payphoneController(http.Controller):

    @http.route(['/payment/payphone/feedback',
                 '/payment/payphone/cancel'], type='http', auth="public",
                methods=['GET'], csrf=False)
    def payphone_payment_feedback(self, **post):
        request.env['payment.transaction'].sudo().form_feedback(post,
                                                                'payphone')
        return werkzeug.utils.redirect("/shop/payment/validate")
