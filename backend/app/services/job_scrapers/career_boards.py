"""Employers whose own career page is read every night.

Each entry is (employer name, applicant system, board id). The board id is the
employer's name in that system's address: jobs.lever.co/<id>,
job-boards.greenhouse.io/<id>, jobs.ashbyhq.com/<id>, <id>.teamtailor.com.

To add an employer, find which system its career page runs on and add a line.
A board that stops answering is logged and skipped; it never fails the run.
Every board here answered with jobs in Sweden on 2026-11-15.
"""
from __future__ import annotations

BOARDS: list[tuple[str, str, str]] = [
    # Greenhouse
    ("Databricks", "greenhouse", "databricks"),
    ("Grafana Labs", "greenhouse", "grafanalabs"),
    ("Mentimeter", "greenhouse", "mentimeter"),
    ("Recorded Future", "greenhouse", "recordedfuture"),
    ("Truecaller", "greenhouse", "truecaller"),
    ("Yubico", "greenhouse", "yubico"),
    # Lever
    ("Avalanche Studios", "lever", "avalanchestudios"),
    ("Netlight", "lever", "netlight"),
    ("Spotify", "lever", "spotify"),
    # Ashby
    ("Epidemic Sound", "ashby", "epidemic-sound"),
    ("Legora", "ashby", "legora"),
    ("Lovable", "ashby", "lovable"),
    ("Planhat", "ashby", "planhat"),
    ("Trustly", "ashby", "trustly"),
    # Teamtailor
    ("Anyfin", "teamtailor", "anyfin"),
    ("Bambuser", "teamtailor", "bambuser"),
    ("Billogram", "teamtailor", "billogram"),
    ("Bokio", "teamtailor", "bokio"),
    ("Detectify", "teamtailor", "detectify"),
    ("Doconomy", "teamtailor", "doconomy"),
    ("Doktor.se", "teamtailor", "doktor"),
    ("Embark Studios", "teamtailor", "embarkstudios"),
    ("Fatshark", "teamtailor", "fatshark"),
    ("Hedvig", "teamtailor", "hedvig"),
    ("Hemnet", "teamtailor", "hemnet"),
    ("HiQ", "teamtailor", "hiq"),
    ("Instabee", "teamtailor", "instabee"),
    ("Lunar", "teamtailor", "lunar"),
    ("Lysa", "teamtailor", "lysa"),
    ("Mathem", "teamtailor", "mathem"),
    ("Natural Cycles", "teamtailor", "naturalcycles"),
    ("Northmill", "teamtailor", "northmill"),
    ("Polestar", "teamtailor", "polestar"),
    ("Qred", "teamtailor", "qred"),
    ("Quinyx", "teamtailor", "quinyx"),
    ("Schibsted", "teamtailor", "schibsted"),
    ("Sellpy", "teamtailor", "sellpy"),
    ("Softhouse", "teamtailor", "softhouse"),
    ("Stegra", "teamtailor", "stegra"),
    ("Storytel", "teamtailor", "storytel"),
    ("Tibber", "teamtailor", "tibber"),
    ("Zenseact", "teamtailor", "zenseact"),
]
