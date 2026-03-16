import GenericUpload from "../components/GenericUpload";

export default function EquityUpload() {
    return (
        <GenericUpload
            title="Upload Equity Trades"
            apiPath="equity"
            redirectPath="/equity"
            previewColumns={[
                { header: "Exchange", accessor: "exchange" },
                { header: "Symbol / Scrip", accessor: "symbol" },
                { header: "ISIN", accessor: "isin" },
                {
                    header: "Qty",
                    accessor: "quantity",
                    format: (val) => Number(val).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                },
                {
                    header: "Avg Price",
                    accessor: "buy_price",
                    format: (val) => Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                },
                { header: "Date", accessor: "buy_date" },
                { header: "Holder", accessor: "holder" },
                { header: "Broker", accessor: "broker" },
            ]}
        />
    );
}
