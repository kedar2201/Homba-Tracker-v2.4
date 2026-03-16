import GenericUpload from "../components/GenericUpload";

export default function MutualFundUpload() {
    return (
        <GenericUpload
            title="Upload Mutual Fund Transactions"
            apiPath="mutual-funds"
            redirectPath="/mutual-funds"
            previewColumns={[
                { header: "Depositor", accessor: "depositor_name" },
                { header: "Code", accessor: "depositor_code" },
                { header: "Scheme Name", accessor: "scheme_name" },
                {
                    header: "Units",
                    accessor: "units",
                    format: (val) => Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
                },
                {
                    header: "Invested Amount",
                    accessor: "invested_amount",
                    format: (val) => Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                },
                { header: "Date", accessor: "transaction_date" },
            ]}
        />
    );
}
