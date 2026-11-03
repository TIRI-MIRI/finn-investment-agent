"""Company data - the demo portfolio and research companies."""

from typing import List

from app.core.models import Company


# Portfolio companies (15-20 NSE/BSE-listed companies)
PORTDATA: List[Company] = [
    Company(
        ticker="RELIANCE",
        name="Reliance Industries Limited",
        exchange="NSE",
        sector="Energy & Petroleum",
        industry="Oil & Gas",
    ),
    Company(
        ticker="HDFCBANK",
        name="HDFC Bank Limited",
        exchange="NSE",
        sector="Banking",
        industry="Financial Services",
    ),
    Company(
        ticker="ICICIBANK",
        name="ICICI Bank Limited",
        exchange="NSE",
        sector="Banking",
        industry="Financial Services",
    ),
    Company(
        ticker="SBIN",
        name="State Bank of India",
        exchange="NSE",
        sector="Banking",
        industry="Financial Services",
    ),
    Company(
        ticker="INFY",
        name="Infosys Limited",
        exchange="NSE",
        sector="IT Services",
        industry="Information Technology",
    ),
    Company(
        ticker="TCS",
        name="Tata Consultancy Services",
        exchange="NSE",
        sector="IT Services",
        industry="Information Technology",
    ),
    Company(
        ticker="WIPRO",
        name="Wipro Limited",
        exchange="NSE",
        sector="IT Services",
        industry="Information Technology",
    ),
    Company(
        ticker="BHARTARTL",
        name="Bharti Airtel Limited",
        exchange="NSE",
        sector="Telecom",
        industry="Telecommunications",
    ),
    Company(
        ticker="LT",
        name="Larsen & Toubro",
        exchange="NSE",
        sector="Engineering & Construction",
        industry="Engineering",
    ),
    Company(
        ticker="TATAMOTORS",
        name="Tata Motors Limited",
        exchange="NSE",
        sector="Automotive",
        industry="Automotive",
    ),
    Company(
        ticker="M&M",
        name="Mahindra & Mahindra",
        exchange="NSE",
        sector="Automotive",
        industry="Automotive",
    ),
    Company(
        ticker="ITC",
        name="ITC Limited",
        exchange="NSE",
        sector="Conglomerate",
        industry="Diversified",
    ),
    Company(
        ticker="HINDUNILVR",
        name="Hindustan Unilever",
        exchange="NSE",
        sector="Consumer Goods",
        industry="Consumer",
    ),
    Company(
        ticker="SUNPHARMA",
        name="Sun Pharmaceutical Industries",
        exchange="NSE",
        sector="Pharmaceuticals",
        industry="Healthcare",
    ),
    Company(
        ticker="DRREDDY",
        name="Dr. Reddy's Laboratories",
        exchange="NSE",
        sector="Pharmaceuticals",
        industry="Healthcare",
    ),
    Company(
        ticker="TATASTEEL",
        name="Tata Steel Limited",
        exchange="NSE",
        sector="Metals & Mining",
        industry="Metals",
    ),
    Company(
        ticker="NTPC",
        name="NTPC Limited",
        exchange="NSE",
        sector="Power",
        industry="Energy",
    ),
    Company(
        ticker="POWERGRID",
        name="Power Grid Corporation of India",
        exchange="NSE",
        sector="Power",
        industry="Energy",
    ),
    Company(
        ticker="ASIANPAINT",
        name="Asian Paints Limited",
        exchange="NSE",
        sector="Consumer Goods",
        industry="Paint & Coatings",
    ),
]


# Research companies (5 companies for detailed Pull workflow)
RESEARCH_DATA: List[Company] = [
    Company(
        ticker="RELIANCE",
        name="Reliance Industries Limited",
        exchange="NSE",
        sector="Energy & Petroleum",
        industry="Oil & Gas",
    ),
    Company(
        ticker="HDFCBANK",
        name="HDFC Bank Limited",
        exchange="NSE",
        sector="Banking",
        industry="Financial Services",
    ),
    Company(
        ticker="INFY",
        name="Infosys Limited",
        exchange="NSE",
        sector="IT Services",
        industry="Information Technology",
    ),
    Company(
        ticker="TCS",
        name="Tata Consultancy Services",
        exchange="NSE",
        sector="IT Services",
        industry="Information Technology",
    ),
    Company(
        ticker="TATAMOTORS",
        name="Tata Motors Limited",
        exchange="NSE",
        sector="Automotive",
        industry="Automotive",
    ),
]
