import CoverLetterEditorClient from "./CoverLetterEditorClient";

export function generateStaticParams() {
    const ids = ["18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "30", "31", "32", "33", "34", "35", "37", "38", "39", "40", "41"];
    return [{ id: 'new' }, ...ids.map((id) => ({ id }))];
}

export default function CoverLetterEditorPage({ params }: { params: Promise<{ id: string }> }) {
    return <CoverLetterEditorClient params={params} />;
}
