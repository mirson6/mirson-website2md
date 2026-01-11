#!/usr/bin/env python3
"""
Quick start examples for the universal documentation crawler.
"""

import subprocess


def run_example(description: str, command: str):
    """Run an example command."""
    print(f"\n{'='*70}")
    print(f"示例: {description}")
    print(f"{'='*70}")
    print(f"命令: {command}")
    print(f"{'='*70}\n")

    response = input("是否运行此示例？(y/n): ")
    if response.lower() == 'y':
        try:
            result = subprocess.run(command, shell=True, check=False)
            if result.returncode == 0:
                print("\n✓ 成功！")
            else:
                print(f"\n✗ 失败 (退出码: {result.returncode})")
        except Exception as e:
            print(f"\n✗ 错误: {e}")
    else:
        print("已跳过")


def main():
    """Show quick start examples."""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║           通用文档自动爬虫 - 快速启动指南                            ║
╚═══════════════════════════════════════════════════════════════════════╝

本工具可以一条命令自动抓取任意路径下的所有文档页面。

使用方法：
    python auto_crawl.py --url <起始页面URL>

    工具会自动：
    1. 从URL中提取基础路径（如 /VBA/, /help/）
    2. 发现该路径下的所有页面
    3. 抓取并聚合到一个Markdown文件

示例用法：
""")

    examples = [
        (
            "爬取VBA文档",
            "python auto_crawl.py --url https://dict.thinktrader.net/VBA/start_now.html"
        ),
        (
            "爬取帮助文档",
            "python auto_crawl.py --url http://ptrade.local.com:7766/hub/help/api"
        ),
        (
            "爬取API文档（自定义输出文件名）",
            "python auto_crawl.py --url https://example.com/docs/api --output api_docs.md"
        ),
        (
            "使用详细日志（调试用）",
            "python auto_crawl.py --url https://dict.thinktrader.net/VBA/start_now.html --verbose"
        ),
    ]

    for i, (description, command) in enumerate(examples, 1):
        print(f"\n{i}. {description}")
        print(f"   {command}")

    print(f"\n{'='*70}")
    print("\n选择一个示例进行测试，或按 Ctrl+C 退出")

    try:
        while True:
            choice = input(f"\n输入示例编号 (1-{len(examples)}) 或 q 退出: ")

            if choice.lower() == 'q':
                print("\n再见！")
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(examples):
                    description, command = examples[idx]
                    run_example(description, command)
                else:
                    print(f"请输入 1-{len(examples)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")

    except KeyboardInterrupt:
        print("\n\n已取消。再见！")


if __name__ == "__main__":
    main()
