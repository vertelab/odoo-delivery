from odoo import models, fields, api
from odoo.exception import UserError
import zeep

class ProductProduct(models.Model):
    _inherit = 'product.product'

    ongoing_article_number = fields.Char(string="Ongoing Article Number")

    def ongoing_article_definition(self):
        self.ensure_one()
        if not self.ongoing_article_number:
           raise UserError(f"Please set an Ongoing article number for product {product.name}.")
        articledefinition = {
           'ArticleOperation': 'CreateOrUpdate',
           'ArticleIdentification': 'ArticleNumber',
           'ArticleNumber': self.ongoing_article_number,
           'ArticleName': 'Odoo Test',
           'ArticleDescription': 'Detta är för att testa att skapa en produkt från Odoo',
           'CountryOfOriginCode': 'SE',
           'Weight': self.weight,
           'NetWeight': self.weight,
           'Volume': self.volume,
           #'Length': 1,
           #'Width': 1,
           #'Height': 1
         }

    def sync_product_to_ongoing(self):
         ongoing_wsdl = self.env.company.ongoing_wsdl
         ongoing_username = self.env.company.ongoing_username
         ongoing_password = self.env.company.ongoin_password
         client = zeep.Client(wsdl=ongoing_wsdl)

        for product in self:
            if product.detailed_type == "product" or product.detailed_type == "consu":
               articledefinition = product.ongoing_article_definition()
               client.service.ProcessArticle(
               GoodsOwnerCode = "Vertel AB",
               UserName = ongoing_username,
               Password = ongoing_password,
               art = articledefinition
               )
               product.message_post(body="Product synced to ongoing successfully.")
