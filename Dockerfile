FROM odoo:13.0
USER root
RUN mkdir /opt/odoo && mkdir /opt/odoo/extra-addons && mkdir /opt/odoo/oca
WORKDIR /opt/odoo/oca
RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/OCA/account-financial-reporting.git --depth 1 --branch 13.0 --single-branch .
COPY sale_customer_credit /opt/odoo/extra-addons/sale_customer_credit
COPY odoo.conf /etc/odoo/odoo.conf
RUN chown -R odoo /opt/odoo
