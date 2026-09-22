// Plant Order Items — group by "Plant Order" (top-right Group By) to get a collapsible dropdown of
// the items under each order number; use the Menu > Export for Excel.
frappe.query_reports["Plant Order Items"] = {
    filters: [
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nKM Confirmed\nIn Production\nInward Complete\nTransfer Billing Done\nCancelled",
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
    ],
    onload(report) {
        report.page.add_inner_message(
            __('Tip: use "Group By → Plant Order" (top-right) to collapse items under each order number; Menu → Export for Excel.')
        );
    },
};
