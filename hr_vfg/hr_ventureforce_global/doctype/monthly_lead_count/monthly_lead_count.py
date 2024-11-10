# Copyright (c) 2024, VFG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta



class MonthlyLeadCount(Document):
	@frappe.whitelist()
	def get_data(self):
		rec = frappe.db.sql("""
		SELECT *,
			SUM(dlcc.total_leads) AS total_tl,
			SUM(dlcc.invalid_leads) AS total_il,
			SUM(dlcc.no_of_calls) AS total_nc
			
		FROM `tabDaily Lead Count` AS dlc
		LEFT JOIN `tabDaily Lead Count CT` AS dlcc
		ON dlcc.parent = dlc.name
		WHERE dlc.date BETWEEN %s and %s
		GROUP BY dlcc.employee	
		""",(self.from_date,self.to_date,), as_dict=1)

		if rec:
			self.daily_lead_count_monthly_ct = []
			for r in rec:
				self.append("daily_lead_count_monthly_ct",{
					"employee":r.employee,
					# "dialer_name":r.dialer_name
					"total_leads": r.total_tl,
					"void_leads":r.total_il,
					"no_of_calls":r.total_nc
				})
			self.save()
	
	def validate(self):
		self.total_quality_leads()
		self.validity_ratio()
		self.invalidity_ratio()
		self.calculate_working_days(self.from_date, self.to_date)
	
	def total_quality_leads(self):
		total_quality_leads = 0
		for row in self.daily_lead_count_monthly_ct:
			void_leads = row.void_leads or 0
			total_leads = row.total_leads or 0
			quality_leads = total_leads - void_leads
			row.total_quality_leads = quality_leads

	def validity_ratio(self):
		validity_ratio = 0
		for row in self.daily_lead_count_monthly_ct:
			total_leads = row.total_leads or 0 
			total_quality_leads = row.total_quality_leads or 0
			validity_ratio = (total_quality_leads / total_leads) * 100
			row.validity_ratio = validity_ratio 
	
	def invalidity_ratio(self):
		invalidity_ratio = 0
		for row in self.daily_lead_count_monthly_ct:
			total_leads = row.total_leads or 0 
			void_leads = row.void_leads or 0
			invalidity_ratio = (void_leads / total_leads) * 100
			row.in_validity_ratio = invalidity_ratio 
	
	def calculate_working_days(self, from_date, to_date):
		# Convert string dates to datetime objects
		from_date = datetime.strptime(from_date, "%Y-%m-%d")
		to_date = datetime.strptime(to_date, "%Y-%m-%d")
		
		# Calculate total working days
		total_working_days = 0
		current_date = from_date
		
		while current_date <= to_date:
			# Check if it's a working day (Monday to Friday)
			if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
				total_working_days += 1
			current_date += timedelta(days=1)

		for row in self.daily_lead_count_monthly_ct:
			row.working_days = total_working_days
		
		return total_working_days

	
