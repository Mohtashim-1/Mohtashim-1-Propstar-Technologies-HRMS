# Copyright (c) 2024, VFG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DailyLeadCount(Document):
	@frappe.whitelist()
	def get_data(self):

		rec = frappe.db.sql("""
		SELECT p.first_name, p.employee_name, p.custom_suffix, p.designation, p.department, p.employee_number, p.name FROM `tabEmployee` AS p WHERE p.status = 'Active'
		""", as_dict=1)

		if rec:
			self.daily_lead_count_ct = []
			for r in rec:
				self.append("daily_lead_count_ct",{
					"employee" : r.employee_name,
					"designation": r.designation,
					"department":r.department
				})
			self.save()
