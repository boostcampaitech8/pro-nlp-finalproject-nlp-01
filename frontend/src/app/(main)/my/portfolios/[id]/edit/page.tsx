import EditPortfolioClient from "./EditPortfolioClient";

export function generateStaticParams() {
    return [{ id: '1' }];
}

export default function EditPortfolioPage({ params }: { params: Promise<{ id: string }> }) {
    return <EditPortfolioClient params={params} />;
}
