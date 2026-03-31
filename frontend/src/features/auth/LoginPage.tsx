import { useAuth } from "./AuthProvider";

export default function LoginPage() {
  const { login } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">StageCrew</h1>
        <p className="text-lg text-gray-600 mb-2">
          演劇団体向けタスク管理SaaS
        </p>
        <p className="text-sm text-gray-400 mb-8">
          物理演劇 / VR演劇 対応
        </p>
        <button
          onClick={login}
          className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
        >
          Discordでログイン
        </button>
      </div>
    </div>
  );
}
