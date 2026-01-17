import RecruitDetailClient from "./RecruitDetailClient";

export function generateStaticParams() {
    return [{ id: '1' }];
}

export default function RecruitDetailPage({ params }: { params: Promise<{ id: string }> }) {
    return <RecruitDetailClient params={params} />;
}
