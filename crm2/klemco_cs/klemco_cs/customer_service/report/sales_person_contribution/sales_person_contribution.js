// Sales Person Contribution — each Sales-Team member's share of Quotations / Sales Orders / Sales
// Invoices, value split by Contribution %. Group By → Sales Person for per-person subtotals.
frappe.query_reports["Sales Person Contribution"] = {
    filters: [
        {
            fieldname: "sales_person",
            label: __("Sales Person"),
            fieldtype: "Link",
            options: "Sales Person",
        },
        {
            fieldname: "document_type",
            label: __("Document Type"),
            fieldtype: "Select",
            options: "\nQuotation\nSales Order\nSales Invoice",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
        },
    ],
    onload(report) {
        report.page.add_inner_message(
            __('Tip: pick a Sales Person to see only their documents; use "Group By → Sales Person" (top-right) for per-person subtotals; Menu → Export for Excel.')
        );
    },
};
