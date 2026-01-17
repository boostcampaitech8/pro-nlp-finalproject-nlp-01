import CoverLetterEditorClient from "./CoverLetterEditorClient";

export function generateStaticParams() {
    return [{ id: 'new' }, { id: '1' }];
}

export default function CoverLetterEditorPage({ params }: { params: Promise<{ id: string }> }) {
    return <CoverLetterEditorClient params={params} />;
}
