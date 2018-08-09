package sandcrawler

import java.text.Normalizer
import java.util.regex.Pattern

object StringUtilities {
  // Adapted from https://git-wip-us.apache.org/repos/asf?p=commons-lang.git;a=blob;f=src/main/java/org/apache/commons/lang3/StringUtils.java;h=1d7b9b99335865a88c509339f700ce71ce2c71f2;hb=HEAD#l934
  def removeAccents(s : String) : String = {
    val replacements = Map(
      '\u0141' -> 'L',
      '\u0142' -> 'l',  // Letter ell
      '\u00d8' -> 'O',
      '\u00f8' -> 'o'
    )
    val sb = new StringBuilder(Normalizer.normalize(s, Normalizer.Form.NFD))
    for (i <- 0 to sb.length - 1) {
      for (key <- replacements.keys) {
        if (sb(i) == key) {
          sb.deleteCharAt(i);
          sb.insert(i, replacements(key))
        }
      }
    }
    val pattern = Pattern.compile("\\p{InCombiningDiacriticalMarks}+")
    pattern.matcher(sb).replaceAll("")
  }

  // Source: https://stackoverflow.com/a/30076541/631051
  def removePunctuation(s: String) : String = {
    s.replaceAll("""[\p{Punct}&&[^.]]""", "")
  }

  // Adapted from: https://stackoverflow.com/a/16018452/631051
  def similarity(s1a : String, s2a : String) : Double = {
    val (s1, s2) = (removeAccents(removePunctuation(s1a)),
      removeAccents(removePunctuation(s2a)))
    val longer : String = if (s1.length > s2.length) s1 else s2
    val shorter : String = if (s1.length > s2.length) s2 else s1
    if (longer.length == 0) {
      // Both strings are empty.
      1
    } else {
      (longer.length - stringDistance(longer, shorter)) / longer.length.toDouble
    }
  }

  // Source: https://oldfashionedsoftware.com/2009/11/19/string-distance-and-refactoring-in-scala/
  def stringDistance(s1: String, s2: String): Int = {
    val memo = scala.collection.mutable.Map[(List[Char],List[Char]),Int]()
    def min(a:Int, b:Int, c:Int) = Math.min( Math.min( a, b ), c)
    def sd(s1: List[Char], s2: List[Char]): Int = {
      if (!memo.contains((s1, s2))) {
        memo((s1,s2)) = (s1, s2) match {
          case (_, Nil) => s1.length
          case (Nil, _) => s2.length
          case (c1::t1, c2::t2)  =>
            min( sd(t1,s2) + 1, sd(s1,t2) + 1,
              sd(t1,t2) + (if (c1==c2) 0 else 1) )
        }
      }
      memo((s1,s2))
    }

    sd( s1.toList, s2.toList )
  }
}

