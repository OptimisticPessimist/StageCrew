import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";

export default function AuthCallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    // 既にセッションが復元済みの場合（リロード、INITIAL_SESSION）もリダイレクト
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        navigate("/", { replace: true });
        return;
      }
    });

    // Supabase がURLフラグメントからセッションを確立した場合のリダイレクト
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN" || event === "INITIAL_SESSION") {
        navigate("/", { replace: true });
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-600">認証中...</p>
    </div>
  );
}
