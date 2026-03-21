import { useParams, Link } from "react-router-dom";
import { useAcceptInvitation } from "./hooks/useInvitations";
import { useState } from "react";

export default function InvitationAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const accept = useAcceptInvitation();
  const [accepted, setAccepted] = useState(false);

  const handleAccept = () => {
    if (!token) return;
    accept.mutate(token, {
      onSuccess: () => setAccepted(true),
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-lg border shadow-sm p-8 max-w-md w-full text-center">
        {accepted ? (
          <>
            <h1 className="text-xl font-bold text-gray-900 mb-2">
              参加完了
            </h1>
            <p className="text-gray-600 mb-4">団体に参加しました。</p>
            <Link
              to="/"
              className="text-indigo-600 hover:text-indigo-700 font-medium"
            >
              ホームへ戻る
            </Link>
          </>
        ) : (
          <>
            <h1 className="text-xl font-bold text-gray-900 mb-2">
              招待を受ける
            </h1>
            <p className="text-gray-600 mb-6">
              この招待リンクから団体に参加できます。
            </p>
            {accept.isError && (
              <p className="text-red-600 text-sm mb-4">
                {(accept.error as Error).message || "エラーが発生しました"}
              </p>
            )}
            <button
              onClick={handleAccept}
              disabled={accept.isPending}
              className="px-6 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {accept.isPending ? "処理中..." : "参加する"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
