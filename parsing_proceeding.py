import argparse

from paper_parsers import (
    AAAIParser,
    AISTATSParser,
    BMVCParser,
    CORLParser,
    CVPRParser,
    ECCVParser,
    ICCVParser,
    ICLRParser,
    ICMLParser,
    ICRAParser,
    IROSParser,
    NIPSParser,
    TPAMIParser,
    WACVParser,
)


def parse_proceeding(
    conference: str,
    year: int,
    file_type: str,
    output_file: str | None = None,
    issue: int | None = None,
):
    """Parse a proceeding of the specified input and save the paper information to a file.

    Args:
        conference: Name of the conference
        year: Year of the proceeding
        file_type: Type of file to store in papers in.
        output_file: Name of the output file to store the papers in
        issue: Optional issue of the journal

    """
    name_to_parser = {
        "AAAI": AAAIParser,
        "AISTATS": AISTATSParser,
        "BMVC": BMVCParser,
        "CORL": CORLParser,
        "CVPR": CVPRParser,
        "ECCV": ECCVParser,
        "ICCV": ICCVParser,
        "ICLR": ICLRParser,
        "ICML": ICMLParser,
        "ICRA": ICRAParser,
        "IROS": IROSParser,
        "NIPS": NIPSParser,
        "TPAMI": TPAMIParser,
        "WACV": WACVParser,
    }

    if issue is None:
        paper_parser = name_to_parser[conference](year=year)
    else:
        try:
            paper_parser = name_to_parser[conference](year=year, issue=issue)
        except KeyError:
            raise KeyError("An issue can solely be passed to journals not conferences.")

    paper_parser.retrieve_papers()
    paper_parser.export_papers(output_file=output_file, file_type=file_type)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-c",
        "--conference",
        choices=[
            "AAAI",
            "AISTATS",
            "BMVC",
            "CORL",
            "CVPR",
            "ECCV",
            "ICCV",
            "ICLR",
            "ICML",
            "ICRA",
            "IROS",
            "NIPS",
            "TPAMI",
            "WACV",
        ],
        help="",
        required=True,
        type=str,
    )
    arg_parser.add_argument(
        "-y" "--year", help="Year of the proceeding.", required=True, type=int
    )
    arg_parser.add_argument(
        "-i",
        "--issue",
        help="Optional issue, if a specific issue is desired. "
        "Only applies to journals.",
        required=False,
        type=int,
        default=None,
    )
    arg_parser.add_argument(
        "-o",
        "--output-file",
        help="Name of the output file to save the papers in. Only use this, if you want to overwrite the default name "
        "based proceeding name/year/issue.",
        type=str,
    )
    arg_parser.add_argument(
        "-f" "--format",
        default="json",
        choices=["json", "csv", "atom_feed"],
        type=str,
        help="Define the file format to store the papers in. By default json is used.",
    )
    input_args = arg_parser.parse_args()

    parse_proceeding(
        conference=input_args.conference,
        year=input_args.year,
        output_file=input_args.output_file,
        file_type=input_args.format,
        issue=input_args.issue,
    )
