# =============================================================================
# Module: newsagent.cli
# Responsibilities: Argument parsing and CLI commands (run/fetch/web/doctor/email-preview).
# Dependencies: config, pipeline, store, web.server, notify, report
# Dependents: __main__, scripts/run.cmd
# ADRs: ADR-0001, ADR-0013
# Traceability: docs/decisions/README.md
# =============================================================================
"""Command line entry point."""

from __future__ import annotations

import argparse
import sys

from .config import load_config
from .keys import KEY_FILENAME, ensure_key_file
from .pipeline import doctor, fetch_sources, run_pipeline
from .store import Store


def _source_ids(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch run/fetch/web/doctor/keys/email-preview/html.

    Preconditions:
        argv is None (sys.argv) or a list of string arguments.
    Postconditions:
        Process exit code: 0 on success, non-zero on configuration/report errors.
        The local keys.txt is created from its template on first use.
    Prohibitions:
        Do not call from library code; use pipeline/api functions directly.
    Raises:
        SystemExit for argparse errors; exceptions from pipeline propagate.
    """
    parser = argparse.ArgumentParser(prog="newsagent", description="AI News Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="抓取 + 去重 + 排序 + LLM 整理 + 生成日报")
    run_parser.add_argument("--no-llm", action="store_true", help="跳过 LLM，输出原始标题")
    run_parser.add_argument("--top", type=int, default=None, help="日报条数（默认配置 20）")
    run_parser.add_argument("--window-days", type=int, default=None, help="展示窗口天数（默认 7）")
    run_parser.add_argument("--sources", default=None, help="只跑指定 source id，逗号分隔")
    run_parser.add_argument("--email", action="store_true", help="生成后把日报发送到配置的邮箱")

    fetch_parser = sub.add_parser("fetch", help="只抓取并入库（不生成日报）")
    fetch_parser.add_argument("--sources", default=None, help="只跑指定 source id，逗号分隔")

    sub.add_parser("doctor", help="自检：配置、密钥、数据库")
    sub.add_parser("keys", help="查看本地密钥文件状态 / 初始化 keys.txt")
    sub.add_parser("market", help="刷新固定关注列表的 90 天股价数据")

    web_parser = sub.add_parser("web", help="启动本地 HTML 界面")
    web_parser.add_argument("--host", default=None, help="监听地址（默认 127.0.0.1）")
    web_parser.add_argument("--port", type=int, default=None, help="端口（默认 8765）")

    sub.add_parser("email-preview", help="生成邮件 HTML 预览（不发送）")
    sub.add_parser("html", help="导出可双击打开的静态 HTML 报告")

    args = parser.parse_args(argv)
    config = load_config()
    key_path, key_created = ensure_key_file(config.root)
    if key_created:
        print(f"首次使用：已创建 {key_path}")
        print(f"请编辑 {KEY_FILENAME}，填入 DEEPSEEK_API_KEY（必填）和 GITHUB_TOKEN（可选）后重新运行。")

    if args.command == "keys":
        deepseek = config.secret("DEEPSEEK_API_KEY", fallback_file="ds_key.txt")
        github = config.secret("GITHUB_TOKEN")
        print(f"keys file       : {key_path}")
        print(f"DEEPSEEK_API_KEY: {'ok' if deepseek else 'MISSING (必填)'}")
        print(f"GITHUB_TOKEN    : {'ok' if github else 'missing (可选)'}")
        print(f"填写方式        : 在项目根目录 {KEY_FILENAME} 中写 KEY=VALUE；也兼容 .env 和 ds_key.txt")
        return 0

    if args.command == "market":
        from .market import fetch_market

        data = fetch_market(config, refresh=True)
        print(f"market: items={len(data.get('items') or [])} errors={len(data.get('errors') or [])} "
              f"as_of={data.get('as_of')}")
        for item in data.get("items") or []:
            print(f"  {item['name']:<6s} {item['code']:<11s} "
                  f"{item['latest']:>10.2f} {item['change_pct']:+.2f}% ({item['latest_date']})")
        return 0

    if args.command == "html":
        from .report import load_report
        from .standalone import render_standalone_html
        from .store import Store

        report = load_report(config)
        if report is None:
            print("还没有日报，先执行 run")
            return 1
        store = Store(config.db_path)
        store.init_schema()
        try:
            trend = store.latest_trend()
        finally:
            store.close()
        path = render_standalone_html(config, report, trend=trend)
        print(path)
        return 0

    if args.command == "email-preview":
        from .notify import write_preview
        from .report import load_report

        report = load_report(config)
        if report is None:
            print("还没有日报，先执行 run")
            return 1
        markdown_path = config.out_dir / str(report["date"]) / "digest.md"
        markdown_text = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
        path = write_preview(config, report, markdown_text)
        print(path)
        return 0

    if args.command == "web":
        from .web.server import serve

        host = args.host or str(config.get("web.host", "127.0.0.1"))
        port = int(args.port or config.get("web.port", 8765))
        serve(config, host=host, port=port)
        return 0

    if args.command == "doctor":
        return doctor(config)

    if args.command == "fetch":
        normalized, errors, stats = fetch_sources(config, source_ids=_source_ids(args.sources))
        store = Store(config.db_path)
        store.init_schema()
        written = store.upsert_items(normalized)
        store.close()
        print(f"fetched={stats['fetched']} accepted={stats['accepted']} "
              f"rejected={stats['rejected']} stored={written} errors={len(errors)}")
        return 0

    stats = run_pipeline(
        config,
        no_llm=args.no_llm,
        top_n=args.top,
        window_days=args.window_days,
        source_ids=_source_ids(args.sources),
        send_email=bool(getattr(args, "email", False)),
    )
    print(stats["digest"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
