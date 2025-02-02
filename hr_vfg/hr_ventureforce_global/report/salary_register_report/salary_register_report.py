from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from frappe.utils import fmt_money


def execute(filters=None):
    columns = get_column()
    data = get_data(filters)
    return columns, data


def get_column():
    column = [
        _("Code") + "::80",
        _("Name") + "::120",
        _("Designation") + "::120",
        _("Department") + "::120",
        _("Holidays") + "::80",
        _("Present") + "::80",
		_("Half Day") + "::80",
		_("Absents") + "::80",
		_("Late") + "::80",
		_("Early") + "::80",
        _("Monthly Salary") + "::100",
        _("Gross Salary") + "::100",
        _("OT Hours") + "::100",
        _("OT Amount") + "::100",
        _("Attendance Allowance") + "::100",
        _("Punctuality Allowance") + "::100",
        _("Performance Allowance") + "::100",
        _("Advance") + "::100",
        _("Loan") + "::100",
        _("Days Ded") + "::100",
        _("Late") + "::100",
        _("Early") + "::100",
        _("Net Salary") + "::100",
    ]
    return column


def get_data(filters):
    cond = {}
    if filters.get("month"):
        cond["month"] = filters.month
    if filters.get("employee"):
        cond["employee"] = filters.employee
    if filters.get("department"):
        cond["department"] = filters.department
    if filters.get("designation"):
        cond["designation"] = filters.designation
    if filters.get("year"):
        cond["year"] = filters.year

    # Fetch salary slips based on the conditions
    salary_slips = frappe.get_all("Salary Slip", filters=cond, fields=["*"])
    data = []

    for sp in salary_slips:
        doc = frappe.get_doc("Salary Slip", sp.name)

        # Initialize variables with defaults
        leaves = sum(lev.taken for lev in getattr(doc, "leave_details", []))
        basic = overtime = att_allow = conv_allow = perf_allow = arrears = 0.0
        abse = late = loan = short = adv = early = 0.0

        # Process earnings
        for ern in doc.earnings:
            component = ern.salary_component.lower()
            if "basic" in component:
                basic += ern.amount
            elif "conveyance" in component:
                conv_allow += ern.amount
            elif "overtime" in component:
                overtime += ern.amount
            elif "attendance" in component:
                att_allow += ern.amount

        # Process deductions
        for ded in getattr(doc, "deductions", []):
            component = ded.salary_component.lower()
            if "absent" in component:
                abse += ded.amount
            elif "advance" in component:
                adv += ded.amount
            elif "late" in component:
                late += ded.amount
            elif "early" in component:
                early += ded.amount
            elif "short" in component:
                short += ded.amount

        ladd = int(late + abse)
        lsld = int(early + short)
        early = int(early)
        late = int(late)

        # Append the row
        row = [
            doc.biometric_id or "",
            doc.employee_name or "",
            doc.designation or "",
            doc.department or "",
            int(doc.total_holidays + doc.total_public_holidays),
            int(doc.custom_present),
			int(doc.custom_half_day),
			int(doc.custom_absents),
			int(doc.custom_total_late),
			int(doc.custom_early),
            int(doc.basic_salary),
            int(doc.gross_pay),
            int(doc.custom_weekends_half_day + doc.custom_weekend_days),
            int(overtime),
            int(att_allow),
            int(0),  # Food Conv is not defined
            int(0),  # Performance Allowance not defined
            int(adv),
            int(loan),
            ladd,
            int(late),
            int(early),
            int(doc.rounded_total),
        ]
        data.append(row)

    return data


@frappe.whitelist()
def get_day_name(date):
    try:
        day = datetime.strptime(str(date), "%Y-%m-%d").weekday()
        return [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ][day]
    except Exception:
        return "Invalid Date"
