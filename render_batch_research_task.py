from __future__ import annotations

import argparse

import batch_research_config as brc


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a batch research task markdown file from a JSON config.")
    parser.add_argument("--config", default=brc.DEFAULT_BATCH_CONFIG_NAME, help="Batch config name without .json")
    parser.add_argument("--round-size", type=int, default=None, help="Override first-round target count")
    parser.add_argument(
        "--output",
        default="cross_asset_batch_task.md",
        help="Output markdown path relative to repo root",
    )
    args = parser.parse_args()

    config = brc.load_batch_research_config(args.config)
    text = brc.render_task_markdown(config, round_size=args.round_size)
    output_path = brc.REPO_DIR / args.output
    output_path.write_text(text, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
