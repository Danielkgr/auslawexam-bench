# Contributing

Thanks for wanting to help with AusLawExam-Bench.

This project is a working benchmarking prototype, and most of the important work is a lawyer checking the provisional questions.  Code contributions are welcome, and the guidance below keeps them safe and reviewable.

## Before you change anything

- Read the README and the code so your change fits what the project already is.
- Open an issue first to describe the change and why it is wanted, and to check it is wanted at all.  A small change to a provisional question set can change a scored number, so say what it affects.

## Making the change

- Fork the repository and work on a branch off the default branch.
- Keep the change small, and explain the reasoning in the commit and the pull request.
- Reference the issue your change addresses, so the reasoning stays with the code.

## Tests and style

- Install the development extras with `pip install -e ".[dev,ui]"`.
- Run the tests with `python3 -m pytest`, and the linter and type checker with `ruff check . && ruff format --check . && mypy`.
- Add a test for any behaviour you change or add, and keep the suite green before you ask for a review.

## Be considerate

Treat everyone here with respect, and assume good faith in feedback.  Explain a change as helpfully as you would like yours explained, and flag any number your change moves rather than hiding it.
