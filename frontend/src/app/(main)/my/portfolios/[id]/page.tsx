import PortfolioDetailClient from "./PortfolioDetailClient";

export function generateStaticParams() {
    const ids = ["35", "37", "38", "39", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "56", "58", "60", "61", "62", "63", "64", "66", "67", "68", "69", "70", "76", "77", "78", "79", "80", "81"];
    return ids.map((id) => ({ id }));
}

export default function PortfolioDetailPage({ params }: { params: Promise<{ id: string }> }) {
    return <PortfolioDetailClient params={params} />;
}
