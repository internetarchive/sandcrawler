
These are notes on how bibliographic metadata matches (of records) and
slugification (to create lookup keys on title strings) worked in the past in
the sandcrawler repository. Eg, circa 2018.

## Scala Slug-ification

Original title strings longer than 1023 characters were rejected (before
slug-ifying).

There was a "slug-denylist". Additionally, scorable strings needed to be
between 8 and 1023 characters (not bytes) long (inclusive)

Slugification transform was:

- lower-case
- remove whitespace ("\s")
- strip specific accent characters:
    '\u0141' -> 'L',
    '\u0142' -> 'l',  // Letter ell
    '\u00d8' -> 'O',
    '\u00f8' -> 'o'
- remove all '\p{InCombiningDiacriticalMarks}'
- remove punctuation:
    \p{Punct}
    ’·“”‘’“”«»「」¿–±§

Partially adapted from apache commons: <https://git-wip-us.apache.org/repos/asf?p=commons-lang.git;a=blob;f=src/main/java/org/apache/commons/lang3/StringUtils.java;h=1d7b9b99335865a88c509339f700ce71ce2c71f2;hb=HEAD#l934>

My original notes/proposal:

1. keep only \p{Ideographic}, \p{Alphabetic}, and \p{Digit}
2. strip accents
3. "lower-case" (unicode-aware)
4. do any final custom/manual mappings

Resulting slugs less than 8 characters long were rejected, and slugs were
checked against a denylist.

Only 554 entries in the denylist; could just ship that in the library.


## Python Tokenization

- "&apos;" -> "'"
- remove non "isalnum()" characters
- encode as ASCII; this removes diacritics etc, but also all non-latin character sets
- optionally remove all whitespace


## Python GROBID Cleanups

These are likely pretty GROBID-specific. Article title was required, but any of
the other filtered-out fields just resulted in partial metadata. These filters
are the result of lots of manual verification of results, and doing things like
taking truncating titles and looking at the most popular prefixes for a large
random sample.

Same denylist for title slugs as Scala, plus:

    editorial
    advertisement
    bookreviews
    reviews
    nr
    abstractoriginalarticle
    originalarticle
    impactfactor
    articlenumber

Other filters on title strings (any of these bad):

- 500 or more characters long
- tokenized string less than 10 characters
- tokenized starts with 'nr' or 'issn'
- lowercase starts with 'int j' or '.int j'
- contains both "volume" and "issue"
- contains "downloadedfrom"
- fewer than 2 or more than 50 tokens (words)
- more than 12 tokens only a single character long
- more than three ":"; more than one "|"; more than one "."

Remove title prefixes (but allow):

    "Title: "
    "Original Article: "
    "Original Article "
    "Article: "

Denylist for authors:

    phd
    phdstudent

Journal name processing:

- apply title denylist
- remove prefixes
    characters: /~&©
    Original Research Article
    Original Article
    Research Article
    Available online www.jocpr.com
- remove suffixes
    Available online at www.sciarena.com
    Original Article
    Available online at
    ISSN
    ISSUE
- remove anywhere
    e-ISSN
    p-ISSN

## Python Grouping Comparison

Would consume joined groups, row-by-row. At most 10 matches per group; any more
and skip (this was for file-to-release).

Overall matching requirements:

- string similarity threshold from scala code
    https://oldfashionedsoftware.com/2009/11/19/string-distance-and-refactoring-in-scala/
    https://stackoverflow.com/questions/955110/similarity-string-comparison-in-java/16018452#16018452
- authors should be consistent
    - convert one author list into space-separated tokens
    - remove "jr." from all author token lists
    - the last word for each author full name in the other list (eg, the lastname),
      tokenized, must be in the token set
- if both years defined, then must match exactly (integers)

In the code, there is a note:

    Note: the actual importer/merger should filter the following patterns out:
    - container title has "letter" and "diar"
    - contribs (authors) contain "&NA;"
    - dates differ (not just year)


## Scala Metadata Keys

Only the titles were ever actually used (in scala), but the keys allowed were:

- title
- authors (list of strings)
- year (int)
- contentType
- doi

