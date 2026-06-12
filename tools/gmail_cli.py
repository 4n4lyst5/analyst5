#!/usr/bin/env python3
"""
CLI Gmail pour Analyst5 — appelé via Bash par l'orchestrateur.
Usage :
  gmail_cli.py send --to X --subject Y --body Z
  gmail_cli.py read [--query Q] [--max N]
  gmail_cli.py thread --id THREAD_ID
  gmail_cli.py auth
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.gmail import (
    send_email, get_recent_emails, get_thread,
    format_emails_for_context, authenticate, is_authenticated
)


def cmd_send(args):
    if not is_authenticated():
        print("Gmail non authentifié. Lance : analyst5 auth gmail")
        sys.exit(1)
    result = send_email(args.to, args.subject, args.body, args.reply_to)
    print(result)


def cmd_read(args):
    if not is_authenticated():
        print("Gmail non authentifié. Lance : analyst5 auth gmail")
        sys.exit(1)
    emails = get_recent_emails(max_results=args.max, query=args.query)
    print(format_emails_for_context(emails))


def cmd_thread(args):
    if not is_authenticated():
        print("Gmail non authentifié. Lance : analyst5 auth gmail")
        sys.exit(1)
    messages = get_thread(args.id)
    for msg in messages:
        print(f"--- De: {msg['from']} | {msg['date']} ---")
        print(msg['body'][:1000])
        print()


def cmd_auth(args):
    authenticate()


def main():
    parser = argparse.ArgumentParser(description="Gmail CLI pour Analyst5")
    sub = parser.add_subparsers(dest="command")

    # send
    p_send = sub.add_parser("send")
    p_send.add_argument("--to",       required=True)
    p_send.add_argument("--subject",  required=True)
    p_send.add_argument("--body",     required=True)
    p_send.add_argument("--reply-to", default=None)

    # read
    p_read = sub.add_parser("read")
    p_read.add_argument("--query", default="is:unread")
    p_read.add_argument("--max",   type=int, default=10)

    # thread
    p_thread = sub.add_parser("thread")
    p_thread.add_argument("--id", required=True)

    # auth
    sub.add_parser("auth")

    args = parser.parse_args()
    if args.command == "send":    cmd_send(args)
    elif args.command == "read":  cmd_read(args)
    elif args.command == "thread": cmd_thread(args)
    elif args.command == "auth":  cmd_auth(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
