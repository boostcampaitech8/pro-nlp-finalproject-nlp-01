import PortfolioDetailClient from "./PortfolioDetailClient";

export function generateStaticParams() {
    return [{ id: '1' }];
}

export default function PortfolioDetailPage({ params }: { params: Promise<{ id: string }> }) {
    return <PortfolioDetailClient params={params} />;
}
