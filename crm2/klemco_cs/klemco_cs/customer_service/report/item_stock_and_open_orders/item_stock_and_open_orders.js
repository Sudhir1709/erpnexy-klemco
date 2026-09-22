// Item Stock & Open Orders — pick an item + a plant (warehouse) to see stock vs. open Sales Orders.
frappe.query_reports["Item Stock and Open Orders"] = {
    filters: [
        {
            fieldname: "item_code",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item",
            reqd: 1,
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse (Plant)"),
            fieldtype: "Link",
            options: "Warehouse",
            reqd: 1,
            get_query: () => ({ filters: { is_group: 0 } }),
        },
    ],
};
