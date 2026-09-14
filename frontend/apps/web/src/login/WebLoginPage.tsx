import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import type { EmailCodeStartResult } from "@mini-auth/auth-ui";
import type { EmailCodeVerifyOptions } from "../authClient";
import { trackUmami } from "../umami";

import "./web-login-page.css";

type LoginLanguage = "zh" | "en";

type WebLoginPageProps = {
  brand: string;
  headline: string;
  mode?: "login" | "register";
  nextValue?: string;
  googleLoginUrl?: string;
  githubLoginUrl?: string;
  demoEmail?: string;
  demoLoginHref?: string;
  onSendCode: (email: string) => Promise<EmailCodeStartResult>;
  onVerifyCode: (email: string, code: string, options?: EmailCodeVerifyOptions) => Promise<void>;
};

type AuthProvider = {
  id: "google" | "github";
  label: string;
  ariaLabel: string;
  href?: string;
  unavailableText: string;
  icon: ReactNode;
};

type EmailCodeFormProps = {
  copy: LoginCopy;
  username: string;
  email: string;
  code: string;
  sentEmail: string;
  showUsername: boolean;
  loading: boolean;
  actionLabel: string;
  onUsernameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onCodeChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

type LoginCopy = {
  headline: Record<"login" | "register", string>;
  providersLabel: string;
  google: string;
  github: string;
  providerUnavailable: string;
  providerUnavailableAria: string;
  divider: string;
  username: string;
  email: string;
  usernamePlaceholder: string;
  emailPlaceholder: string;
  codeSentTo: (email: string) => string;
  continue: string;
  sending: string;
  continuing: string;
  noAccount: string;
  createOne: string;
  alreadyHaveAccount: string;
  signIn: string;
  demoLogin: string;
  didntReceiveCode: string;
  resendCode: string;
  resendCodeWithCooldown: (seconds: number) => string;
  poweredBy: string;
  debugCode: (code: string) => string;
  errors: {
    usernameRequired: string;
    emailRequired: string;
    sendFailed: string;
    signInFailed: string;
  };
};

const LOGIN_COPY: Record<LoginLanguage, LoginCopy> = {
  zh: {
    headline: {
      login: "欢迎回来",
      register: "创建你的 Minibot 账号",
    },
    providersLabel: "登录方式",
    google: "使用 Google 继续",
    github: "使用 GitHub 继续",
    providerUnavailable: "暂未接入",
    providerUnavailableAria: "暂未接入",
    divider: "或",
    username: "用户名",
    email: "邮箱",
    usernamePlaceholder: "请输入用户名",
    emailPlaceholder: "请输入邮箱",
    codeSentTo: (email) => `验证码已发送至 ${email}`,
    continue: "继续",
    sending: "发送中...",
    continuing: "登录中...",
    noAccount: "还没有账号？",
    createOne: "创建账号",
    alreadyHaveAccount: "已有账号？",
    signIn: "登录",
    demoLogin: "Demo 账号登录",
    didntReceiveCode: "没收到验证码？",
    resendCode: "重新发送",
    resendCodeWithCooldown: (seconds) => `重新发送 (${seconds}s)`,
    poweredBy: "Powered by",
    debugCode: (code) => `调试验证码：${code}`,
    errors: {
      usernameRequired: "请输入用户名。",
      emailRequired: "请输入邮箱。",
      sendFailed: "验证码发送失败，请稍后重试。",
      signInFailed: "登录失败，请稍后重试。",
    },
  },
  en: {
    headline: {
      login: "Hey friend! Welcome back",
      register: "Create your Minibot account",
    },
    providersLabel: "Sign in providers",
    google: "Continue with Google",
    github: "Continue with GitHub",
    providerUnavailable: "Coming soon",
    providerUnavailableAria: "coming soon",
    divider: "Or",
    username: "Username",
    email: "Email",
    usernamePlaceholder: "Enter username",
    emailPlaceholder: "Enter email",
    codeSentTo: (email) => `Code sent to ${email}`,
    continue: "Continue",
    sending: "Sending...",
    continuing: "Continuing...",
    noAccount: "No account?",
    createOne: "Create one",
    alreadyHaveAccount: "Already have an account?",
    signIn: "Sign in",
    demoLogin: "Demo account login",
    didntReceiveCode: "Didn't receive a code?",
    resendCode: "Resend code",
    resendCodeWithCooldown: (seconds) => `Resend code (${seconds}s)`,
    poweredBy: "Powered by",
    debugCode: (code) => `Debug code: ${code}`,
    errors: {
      usernameRequired: "Please enter your username.",
      emailRequired: "Please enter your email.",
      sendFailed: "Could not send the code. Please try again.",
      signInFailed: "Sign in failed. Please try again.",
    },
  },
};

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

function GoogleIcon() {
  return (
    <svg aria-hidden="true" className="mini-login-provider-icon" viewBox="0 0 24 24">
      <path fill="#4285f4" d="M22.6 12.2c0-.7-.1-1.3-.2-1.9H12v3.7h6c-.3 1.4-1 2.5-2.1 3.2v2.7h3.4c2-1.8 3.3-4.5 3.3-7.7Z" />
      <path fill="#34a853" d="M12 23c3 0 5.5-1 7.3-3.1l-3.4-2.7c-1 .6-2.2 1-3.9 1-3 0-5.5-2-6.4-4.7H2.1v2.8C3.9 20.2 7.7 23 12 23Z" />
      <path fill="#fbbc05" d="M5.6 13.5c-.2-.7-.4-1.4-.4-2.2s.1-1.5.4-2.2V6.3H2.1C1.4 7.8 1 9.5 1 11.3s.4 3.5 1.1 5l3.5-2.8Z" />
      <path fill="#ea4335" d="M12 4.4c1.6 0 3.1.6 4.2 1.7l3.1-3.1C17.5 1.1 15 0 12 0 7.7 0 3.9 2.8 2.1 6.3l3.5 2.8C6.5 6.4 9 4.4 12 4.4Z" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg aria-hidden="true" className="mini-login-provider-icon" viewBox="0 0 24 24">
      <path fill="currentColor" d="M12 1.8a10.3 10.3 0 0 0-3.3 20c.5.1.7-.2.7-.5v-1.8c-2.8.6-3.4-1.2-3.4-1.2-.5-1.1-1.1-1.4-1.1-1.4-.9-.6.1-.6.1-.6 1 .1 1.6 1.1 1.6 1.1.9 1.6 2.4 1.1 2.9.8.1-.7.4-1.1.7-1.4-2.2-.3-4.6-1.1-4.6-5 0-1.1.4-2 1-2.8-.1-.3-.5-1.3.1-2.8 0 0 .9-.3 2.8 1a9.7 9.7 0 0 1 5.1 0c2-1.3 2.8-1 2.8-1 .6 1.5.2 2.5.1 2.8.7.8 1 1.7 1 2.8 0 3.9-2.4 4.7-4.6 5 .4.3.8 1 .8 2v2.9c0 .3.2.6.8.5A10.3 10.3 0 0 0 12 1.8Z" />
    </svg>
  );
}

function ProviderButton({ provider }: { provider: AuthProvider }) {
  const content = (
    <>
      {provider.icon}
      <span>{provider.label}</span>
      <span className="mini-login-provider-overlay" aria-hidden="true">
        {provider.unavailableText}
      </span>
    </>
  );

  if (provider.href) {
    return (
      <a
        className="mini-login-provider"
        href={provider.href}
        aria-label={provider.label}
        onClick={() => trackUmami("oauth_start", { method: provider.id })}
      >
        {provider.icon}
        <span>{provider.label}</span>
      </a>
    );
  }

  return (
    <button className="mini-login-provider is-disabled" type="button" aria-label={provider.ariaLabel} disabled>
      {content}
    </button>
  );
}

function ProviderSection({ providers, label }: { providers: AuthProvider[]; label: string }) {
  return (
    <div className="mini-login-providers" aria-label={label}>
      {providers.map((provider) => (
        <ProviderButton key={provider.id} provider={provider} />
      ))}
    </div>
  );
}

function EmailCodeForm({
  copy,
  username,
  email,
  code,
  sentEmail,
  showUsername,
  loading,
  actionLabel,
  onUsernameChange,
  onEmailChange,
  onCodeChange,
  onSubmit,
}: EmailCodeFormProps) {
  return (
    <form className="mini-login-form" onSubmit={onSubmit}>
      {showUsername ? (
        <label className="mini-login-field">
          <span>{copy.username}</span>
          <input
            type="text"
            value={username}
            onChange={(event) => onUsernameChange(event.target.value)}
            autoComplete="username"
            placeholder={copy.usernamePlaceholder}
          />
        </label>
      ) : null}

      <label className="mini-login-field">
        <span>{copy.email}</span>
        <input
          type="email"
          value={email}
          onChange={(event) => onEmailChange(event.target.value)}
          autoComplete="email"
          placeholder={copy.emailPlaceholder}
        />
      </label>

      {sentEmail ? (
        <label className="mini-login-field">
          <span className="mini-login-code-hint">{copy.codeSentTo(sentEmail)}</span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(event) => onCodeChange(event.target.value)}
          />
        </label>
      ) : null}

      <button className="mini-login-continue" type="submit" disabled={loading}>
        {actionLabel}
      </button>
    </form>
  );
}

function LoginSupportText({
  mode,
  copy,
  sentEmail,
  canResend,
  cooldown,
  demoLoginHref,
  onResend,
}: {
  mode: "login" | "register";
  copy: LoginCopy;
  sentEmail: string;
  canResend: boolean;
  cooldown: number;
  demoLoginHref?: string;
  onResend: () => void;
}) {
  if (sentEmail) {
    return (
      <p className="mini-login-resend">
        {copy.didntReceiveCode}{" "}
        <button type="button" onClick={onResend} disabled={!canResend}>
          {cooldown > 0 ? copy.resendCodeWithCooldown(cooldown) : copy.resendCode}
        </button>
      </p>
    );
  }

  return (
    <p className="mini-login-resend">
      {mode === "register" ? `${copy.alreadyHaveAccount} ` : `${copy.noAccount} `}
      <a href={mode === "register" ? "/" : "/register"}>{mode === "register" ? copy.signIn : copy.createOne}</a>
      {mode === "login" && demoLoginHref ? (
        <>
          <span aria-hidden="true"> · </span>
          <a href={demoLoginHref}>{copy.demoLogin}</a>
        </>
      ) : null}
    </p>
  );
}

function LoginFooter({ brand, copy, language }: { brand: string; copy: LoginCopy; language: LoginLanguage }) {
  return (
    <footer className="mini-login-footer">
      <p>
        {copy.poweredBy} <strong>{brand}</strong>
      </p>
      <p className="mini-login-legal-links">
        <a href="/privacy">{language === "zh" ? "隐私政策" : "Privacy Policy"}</a>
        <span aria-hidden="true"> · </span>
        <a href="/terms">{language === "zh" ? "服务条款" : "Terms of Service"}</a>
      </p>
    </footer>
  );
}

function LanguageSwitcher({
  language,
  onChange,
}: {
  language: LoginLanguage;
  onChange: (language: LoginLanguage) => void;
}) {
  return (
    <div className="mini-login-language" aria-label="语言切换">
      <button
        type="button"
        className={language === "zh" ? "is-active" : ""}
        aria-pressed={language === "zh"}
        aria-label="切换到中文"
        onClick={() => onChange("zh")}
      >
        中
      </button>
      <span aria-hidden="true">/</span>
      <button
        type="button"
        className={language === "en" ? "is-active" : ""}
        aria-pressed={language === "en"}
        aria-label="Switch to English"
        onClick={() => onChange("en")}
      >
        EN
      </button>
    </div>
  );
}

export function WebLoginPage({
  brand,
  headline: _headline,
  mode = "login",
  nextValue = "",
  googleLoginUrl,
  githubLoginUrl,
  demoEmail = "",
  demoLoginHref,
  onSendCode,
  onVerifyCode,
}: WebLoginPageProps) {
  const [language, setLanguage] = useState<LoginLanguage>("zh");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(demoEmail);
  const [code, setCode] = useState("");
  const [sentEmail, setSentEmail] = useState("");
  const [debugCode, setDebugCode] = useState("");
  const [error, setError] = useState("");
  const [loadingSend, setLoadingSend] = useState(false);
  const [loadingVerify, setLoadingVerify] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const isDevelopment = import.meta.env.DEV;
  const isBusy = loadingSend || loadingVerify;
  const isRegister = mode === "register";
  const copy = LOGIN_COPY[language];
  const canResend = cooldown === 0 && !loadingSend;
  const actionLabel = loadingVerify ? copy.continuing : loadingSend ? copy.sending : copy.continue;

  const providers = useMemo<AuthProvider[]>(
    () => [
      {
        id: "google",
        label: copy.google,
        ariaLabel: googleLoginUrl ? copy.google : `${copy.google}${language === "zh" ? "，" : ", "}${copy.providerUnavailableAria}`,
        href: googleLoginUrl,
        unavailableText: copy.providerUnavailable,
        icon: <GoogleIcon />,
      },
      {
        id: "github",
        label: copy.github,
        ariaLabel: githubLoginUrl ? copy.github : `${copy.github}${language === "zh" ? "，" : ", "}${copy.providerUnavailableAria}`,
        href: githubLoginUrl,
        unavailableText: copy.providerUnavailable,
        icon: <GitHubIcon />,
      },
    ],
    [copy.github, copy.google, copy.providerUnavailable, copy.providerUnavailableAria, githubLoginUrl, googleLoginUrl, language],
  );

  useEffect(() => {
    document.title = `${brand} 登录`;
  }, [brand]);

  useEffect(() => {
    if (cooldown <= 0) return;

    const timer = window.setInterval(() => {
      setCooldown((current) => Math.max(0, current - 1));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [cooldown]);

  const startEmailLogin = async () => {
    if (isRegister && !username.trim()) {
      setError(copy.errors.usernameRequired);
      return;
    }

    const normalized = normalizeEmail(email);
    if (!normalized) {
      setError(copy.errors.emailRequired);
      return;
    }

    setError("");
    setLoadingSend(true);
    try {
      const result = await onSendCode(normalized);
      setSentEmail(result.email || normalized);
      setDebugCode(result.debug_code || "");
      setCooldown(result.resend_after_seconds || 60);
      if (result.debug_code) {
        setCode(result.debug_code);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.errors.sendFailed);
    } finally {
      setLoadingSend(false);
    }
  };

  const verifyEmailLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isRegister && !username.trim()) {
      setError(copy.errors.usernameRequired);
      return;
    }

    const normalized = normalizeEmail(email);
    if (!normalized) {
      setError(copy.errors.emailRequired);
      return;
    }

    if (!code.trim()) {
      await startEmailLogin();
      return;
    }

    setError("");
    setLoadingVerify(true);
    try {
      await onVerifyCode(normalized, code.trim(), isRegister ? { username: username.trim() } : undefined);
      trackUmami(isRegister ? "sign_up" : "login", { method: "email" });
      window.location.assign(nextValue || "/docs");
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.errors.signInFailed);
    } finally {
      setLoadingVerify(false);
    }
  };

  return (
    <main className="mini-login-page">
      <LanguageSwitcher language={language} onChange={setLanguage} />
      <section className="mini-login-panel" aria-labelledby="mini-login-title">
        <a className="mini-login-brand" href="/" aria-label={brand}>
          {brand}
        </a>

        <h1 id="mini-login-title">{copy.headline[mode]}</h1>

        <ProviderSection providers={providers} label={copy.providersLabel} />
        <div className="mini-login-divider">{copy.divider}</div>

        {error ? <div className="mini-login-error">{error}</div> : null}

        <EmailCodeForm
          copy={copy}
          username={username}
          email={email}
          code={code}
          sentEmail={sentEmail}
          showUsername={isRegister}
          loading={isBusy}
          actionLabel={actionLabel}
          onUsernameChange={setUsername}
          onEmailChange={setEmail}
          onCodeChange={setCode}
          onSubmit={verifyEmailLogin}
        />

        <LoginSupportText
          mode={mode}
          copy={copy}
          sentEmail={sentEmail}
          canResend={canResend}
          cooldown={cooldown}
          demoLoginHref={demoLoginHref}
          onResend={startEmailLogin}
        />

        {debugCode && isDevelopment ? <div className="mini-login-debug">{copy.debugCode(debugCode)}</div> : null}

        <LoginFooter brand={brand} copy={copy} language={language} />
      </section>
    </main>
  );
}
