import { useEffect, useRef } from "react";

declare global {
  interface Window {
    smartCaptcha?: {
      render: (
        el: HTMLElement,
        opts: { sitekey: string; callback: (token: string) => void; hl?: string }
      ) => number;
    };
  }
}

const CLIENT_KEY = import.meta.env.VITE_SMARTCAPTCHA_CLIENT_KEY ?? "";

/** Яндекс SmartCaptcha. Если клиентский ключ не задан — ничего не рендерим. */
export function SmartCaptcha({ onToken }: { onToken: (token: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!CLIENT_KEY || !ref.current) return;

    const render = () => {
      if (window.smartCaptcha && ref.current) {
        window.smartCaptcha.render(ref.current, {
          sitekey: CLIENT_KEY,
          hl: "ru",
          callback: onToken,
        });
      }
    };

    if (window.smartCaptcha) {
      render();
    } else {
      const script = document.createElement("script");
      script.src = "https://smartcaptcha.yandexcloud.net/captcha.js";
      script.async = true;
      script.onload = render;
      document.head.appendChild(script);
    }
  }, [onToken]);

  if (!CLIENT_KEY) return null;
  return <div ref={ref} style={{ marginTop: 12 }} />;
}

export const captchaEnabled = Boolean(CLIENT_KEY);
