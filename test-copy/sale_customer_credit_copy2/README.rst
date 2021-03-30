Customer Credit Policy
======================

This module provides functionality to classify customers according to credit policies
and do spcific action when a customer exceed a policy limit

Usage
=====

#Go to Invoicing > Configuration > Customers Credit Policy.
#Create a new Policy.
#    Add limits with `Limit amount` and `Effect After Days` and specify action to be done in every case.

#Go to Sales > Orders > Customers.
In form View:

#Go to Invoicing Tab.
#Select Specific Credit Policy.

Now every day there will be a scheduled job that will check customer's outstanding and aproprate action.
