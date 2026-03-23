"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api";
import { getStoredAccessToken, setStoredAccessToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (getStoredAccessToken()) {
      router.replace("/");
    }
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await login(username, password);
      setStoredAccessToken(response.access_token);
      router.push("/");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Accesso non riuscito");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-wrap">
      <section className="login-card">
        <p className="badge">Login applicativo</p>
        <h1>Accesso piattaforma</h1>
        <p>
          Questa schermata usa il backend FastAPI reale. Inserisci credenziali
          applicative valide per ottenere un token JWT e caricare la dashboard.
        </p>

        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="username">
            Username o email
            <input
              id="username"
              name="username"
              type="text"
              placeholder="utente@ente.local"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>

          <label htmlFor="password">
            Password
            <input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          {error ? <p className="status-note error-text">{error}</p> : null}

          <button className="button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Accesso in corso..." : "Accedi"}
          </button>
        </form>
      </section>
    </main>
  );
}
