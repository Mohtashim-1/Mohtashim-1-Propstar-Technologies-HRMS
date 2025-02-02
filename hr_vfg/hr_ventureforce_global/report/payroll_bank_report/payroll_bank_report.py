from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime


def execute(filters=None):
    columns = get_column()
    data = get_data(filters)
    return columns, data


def get_column():
    return [
        _("Code") + "::80",
        _("Name") + "::120",
        _("Bank Account No") + "::120",
        _("Net Salary") + "::100",
        _("Bank Name") + "::120",
        _("Account Title") + "::100",
    ]


def get_data(filters):
    cond = {}
    if filters.get("month"):
        cond["month"] = filters.month
    if filters.get("employee"):
        cond["employee"] = filters.employee
    if filters.get("year"):
        cond["year"] = filters.year

    # Fetch salary slips based on the conditions
    salary_slips = frappe.get_all("Salary Slip", filters=cond, fields=["*"])
    data = []

    for sp in salary_slips:
        doc = frappe.get_doc("Salary Slip", sp.name)

        # Initialize variables with defaults
        late = abse = early = short = 0.0

        # Process earnings and deductions
        for ern in doc.earnings:
            component = ern.salary_component.lower()
            if "basic" in component:
                continue
            elif "conveyance" in component:
                continue
            elif "overtime" in component:
                continue
            elif "attendance" in component:
                continue

        for ded in getattr(doc, "deductions", []):
            component = ded.salary_component.lower()
            if "absent" in component:
                abse += ded.amount
            elif "advance" in component:
                continue
            elif "late" in component:
                late += ded.amount
            elif "early" in component:
                early += ded.amount
            elif "short" in component:
                short += ded.amount

        formatted_total = "{:,.0f}".format(doc.rounded_total)

        # Append the row
        row = [
            doc.biometric_id or "",
            doc.employee_name or "",
            doc.bank_account_no or "",
            formatted_total,
            doc.bank_name or "",
            doc.custom_account_title or "",
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
