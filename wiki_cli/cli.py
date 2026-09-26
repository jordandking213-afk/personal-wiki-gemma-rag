"""Command-line entry point: `./wiki <command>`. Parses the command, picks the mode, and
hands off to the harness (ingest.py, modes.py). All model calls go to local Ollama."""
import argparse
import sys

from . import config, llm

EPILOG = f"""
modes:
  search  shows original passages from vault/raw with paths; no answer is generated and
          the model does not need to be running
  ask     standalone factual answer from retrieved passages with [S#] citations, or
          "INSUFFICIENT EVIDENCE"; ignores chat history and personality
  chat    warm study companion with conversation memory; looks up notes only when needed

examples:
  ./wiki ingest vault/raw
  ./wiki search "living sacrifice"
  ./wiki ask "What are the three groans in Romans 8:18-30?"
  ./wiki chat

configuration (wiki_cli/config.py):
  model   {config.MODEL} served by Ollama at {config.OLLAMA_URL}
  prompts prompts/persona.md (chat), prompts/wiki-instructions.md (ask)
  data    vault/raw (sources), vault/wiki (pages), data/ (index, manifest), evidence/ (saved runs)

requires: Ollama running (`ollama serve`) with the model pulled (`ollama pull {config.MODEL}`)
for ingest, ask, and chat. search works without it.
"""


def add_mode_flag(p):
    p.add_argument("--mode", choices=["local", "online"], default="local",
                   help="where the model runs (default: local; online is not implemented)")


def check_mode(args):
    if getattr(args, "mode", "local") != "local":
        sys.exit("Error: online mode is not implemented in this project. Local mode is the default "
                 "and works fully offline; run without --mode or with --mode local.")


def cmd_ingest(args):
    from .ingest import ingest
    print(f"Ingesting {args.path} with {config.MODEL} (local)")
    ingest(args.path, force=args.force)


def cmd_search(args):
    from .modes import run_search
    run_search(args.query, k=args.k, save=not args.no_save)


def cmd_ask(args):
    check_mode(args)
    from .modes import run_ask
    run_ask(args.question, save=not args.no_save)


def cmd_chat(args):
    check_mode(args)
    from .modes import run_chat
    run_chat(save=not args.no_save)


def build_parser():
    p = argparse.ArgumentParser(
        prog="wiki",
        description="Romans Study Wiki: a personal wiki CLI powered by local Gemma "
                    f"({config.MODEL} via Ollama). Runs fully offline once the model is downloaded.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("ingest", help="read raw notes, generate linked wiki pages with Gemma, rebuild the search index")
    s.add_argument("path", nargs="?", default=str(config.RAW_DIR), help="a raw .md file or folder (default: vault/raw)")
    s.add_argument("--force", action="store_true", help="re-run Gemma even if the source is unchanged")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("search", help="show matching original passages and source paths (no model call)")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=5, help="number of passages to show (default 5)")
    s.add_argument("--no-save", action="store_true", help="do not write to evidence/")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("ask", help="standalone, cited answer from the notes (or insufficient evidence)")
    s.add_argument("question")
    add_mode_flag(s)
    s.add_argument("--no-save", action="store_true", help="do not write to evidence/")
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("chat", help="talk with the study companion (conversation context, optional notes lookup)")
    add_mode_flag(s)
    s.add_argument("--no-save", action="store_true", help="do not write a transcript to evidence/")
    s.set_defaults(func=cmd_chat)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return
    try:
        args.func(args)
    except llm.ModelUnavailable as e:
        sys.exit(f"Error: {e}")
    except FileNotFoundError as e:
        sys.exit(f"Error: {e}")
    except KeyboardInterrupt:
        sys.exit("\nInterrupted.")
