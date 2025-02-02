// Copyright (c) 2025, VFG and contributors
// For license information, please see license.txt

frappe.query_reports["Payroll Bank Report"] = {
	"filters": [
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			
		},
		{
			"fieldname":"month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options":"\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
			"reqd": 1
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Link",
			"options":"Year",
			"reqd": 1
		},
		{
			"fieldname":"department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options":"Department",
			// "reqd": 1
		},
		{
			"fieldname":"designation",
			"label": __("Designation"),
			"fieldtype": "Link",
			"options":"Designation",
			// "reqd": 1
		},

	]
};


frappe.query_reports["Salary Register Report"] = {
    formatter: function (value, row, column, data, default_formatter) {
        // Apply the default formatter
        value = default_formatter(value, row, column, data);

        // Highlight earnings in green
        if (["OT Amount", "Attendance Allowance", "Punctuality Allowance", "Performance Allowance","Attendance Allowance","Puntuality Allowance","Performance Allowance"].includes(column.label)) {
            if (data[column.fieldname] > 0) {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            }
        }

        // Highlight deductions in red
        if (["Advance", "Loan", "Days Ded", "Late", "Early"].includes(column.label)) {
            if (data[column.fieldname] > 0) {
                value = `<span style="color: red; font-weight: bold;">${value}</span>`;
            }
        }

		// Highlight deductions in orange
        if (["Net Salary"].includes(column.label)) {
            if (data[column.fieldname] > 0) {
                value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
            }
        }

        return value;
    },
};
