import GenericUpload from "../components/GenericUpload";

export default function FDUpload() {
    return (
        <GenericUpload
            title="Upload Fixed Deposits"
            apiPath="fixed-deposits"
            redirectPath="/fixed-deposits"
            previewColumns={[
                { header: "Bank", accessor: "bank_name" },
                { header: "Depositor", accessor: "depositor_name" },
                { header: "Code", accessor: "depositor_code" },
                { header: "FD No", accessor: "fd_code" },
                {
                    header: "Principal",
                    accessor: "principal",
                    format: (val) => Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                },
                {
                    header: "Rate",
                    accessor: "interest_rate",
                    format: (val) => Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                },
                { header: "Compounding", accessor: "compounding_frequency" },
                { header: "Payout", accessor: "payout_type" },
                { header: "Start Date", accessor: "start_date" },
                { header: "Maturity", accessor: "maturity_date" },
            ]}
        />
    );
}
