import FinanceDataReader as fdr


def main() -> None:
    print(f"FinanceDataReader {fdr.__version__}")

    symbols = fdr.StockListing("KRX").head(5)
    print(symbols[["Code", "Name", "Market"]].to_string(index=False))


if __name__ == "__main__":
    main()
