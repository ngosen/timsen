# Prior work

What others learned building the same kind of thing, and what it means for this project. Read on
2026-10-17; each claim links to where it was read. A claim backed by one source only says so.

## Input methods keep n-grams at the core

- Statistical pinyin input methods have three parts: an n-gram language model, a Viterbi search
  and the user interface; learning from the user is listed as future work
  ([Zhang et al., ISCSLP 2000](https://www.isca-archive.org/iscslp_2000/zhang00i_iscslp.pdf)).
  Later pinyin input methods add user-defined phrases in a user dictionary
  ([Wikipedia](https://en.wikipedia.org/wiki/Pinyin_input_method)).
- A neural language model was about 100 times slower than a back-off n-gram for a pinyin input
  method, so its probabilities were written back into the n-gram table; conversion accuracy rose by
  0.1 to 1 point ([Y15-1052, PACLIC 2015](https://aclanthology.org/Y15-1052.pdf)). No neural restore
  model was trained here; the small LSTM for next words gained 1 point of top-3 recall on chat over
  the table ("A small LSTM for next-word suggestions" in `EXPERIMENTS.md`).

## Published accuracy for restoring Vietnamese marks

- Phrase-based statistical translation restored 97.32% of words and a neural translation model
  96.15%, on about 17,600 test sentences from news articles
  ([arXiv 1709.07104](https://arxiv.org/html/1709.07104v2)).
- Tim Sen's tables score 94.84% (small) and 96.55% (large) on Wikipedia, in the same range but on a
  different test set, so the figures are not comparable. Their size and speed were not checked.

## Next-word suggestions are often wrong, even at Google

- Gboard, on real typing logs: the n-gram model has the next word in its top 3 for 22.1% of words,
  a 1.4 MB CIFG (a small LSTM) for 27.1%; keyboard response is expected within 20 ms
  ([Hard et al., 2018](https://arxiv.org/html/1811.03604v2)). The neural gain came with in-domain
  training data this project does not collect.
- In a crowd-sourced study of 170 people, word suggestions saved 3.43 characters per phrase but cost
  about two seconds, so they slowed typing
  ([Alharbi et al., 2020](https://www.researchgate.net/publication/347484031_The_Effects_of_Predictive_Features_of_Mobile_Keyboards_on_Text_Entry_Speed_and_Errors);
  single study).

## Automatic correction pays only when it is rarely wrong

- Expert typists were 10 words a minute faster with a perfectly accurate autocorrect than with one
  that is always wrong, but they still avoided leaving errors for it, because fixing a wrong
  correction is slow ([Banovic et al., MobileHCI 2019](https://dl.acm.org/doi/pdf/10.1145/3338286.3340126)).
- Fixing a wrong autocorrection took 5.5 seconds on average
  ([Alharbi et al., 2020](https://www.researchgate.net/publication/347484031_The_Effects_of_Predictive_Features_of_Mobile_Keyboards_on_Text_Entry_Speed_and_Errors)).
- Both studies are on phones and in English; on a physical keyboard undoing may be faster.

Restoring marks is a correction applied to every word: at 92% one word in twelve needs fixing, so
the cost of the undo key (Tab) and the confidence shown per word matter as much as accuracy.

## Vietnamese tools that add marks

| Tool | What it does | How it differs |
|---|---|---|
| Cốc Cốc browser, spell check | Adds marks to text typed without them in web page text fields, since about 2013 | Only inside that browser; until April 2018 the typed text went to its servers |
| [TocKyVNKey](https://taimienphi.vn/download-tockyvnkey-5725) | Windows input method that adds marks to words typed without them, from a dictionary, and expands shorthand | Windows only, closed source; accuracy and context use unknown |
| Laban Key (Zalo) | Phone keyboard; users report marked suggestions from unmarked typing | Phone only; its [App Store listing](https://apps.apple.com/vn/app/laban-key-g%C3%B5-ti%E1%BA%BFng-vi%E1%BB%87t/id929865547?l=vi) claims spell check and next-word suggestions, not marks for unmarked typing |
| [v7](https://github.com/ducngg/v7) (IJCAI 2025) | Abbreviated input such as `x0ch2` → `xin chào`, nanoGPT model | A new way of typing to learn; macOS and Windows, no Linux |
| [vietnameseaccent.com](https://vietnameseaccent.com/), [chuvietnhanh](https://chuvietnhanh.sourceforge.net/TuDongThemDauTiengViet.htm) | Paste text, press a button | Not an input method; the first links to the XLM-R model measured here at 86.9% on wiki |

Cốc Cốc in detail:

- The feature was announced in 2013 with spell check, which was claimed to be about 94% accurate
  ([VnExpress, 2013-11-05](https://vnexpress.net/coc-coc-ra-mat-cong-cu-kiem-tra-chinh-ta-ngay-tren-trinh-duyet-2905445.html)).
  In 2014 it was described as adding marks "anywhere on the internet"
  ([Thanh Niên, 2014-09-29](https://thanhnien.vn/coc-coc-them-tinh-nang-tra-tu-dien-khi-luot-web-185386369.htm)).
  It is still listed today under spell check, which "adds Vietnamese marks to text written without
  them" ([features page](https://coccoc.com/desktop/features),
  [spell check page](https://coccoc.com/kiem-tra-chinh-ta)). The browser has a Linux build
  ([install guide](https://support.coccoc.com/desktop/tai-ve-va-cai-dat-coc-coc-cho-may-tinh-linux));
  whether the feature works there was not checked.
- In 2018, users found that what they typed in text fields, private messages included, was sent to
  `spell.itim.vn`. The head of browser development replied that spell check and adding marks
  require sending the text fields to the server, anonymously and stored only temporarily. The same
  article says the release of 16 April 2018 no longer sent the typed text
  ([VietNamNet, 2018-04-17](https://vietnamnet.vn/thuc-hu-chuyen-coc-coc-bi-mat-thu-thap-thong-tin-nguoi-dung-i372394.html);
  single source). How it works today was not checked.

What this means here: adding marks while typing is not new. A large Vietnamese company has kept it
in its browser for over ten years, which suggests people want it, and TocKyVNKey does it on Windows.
What none of the tools above does is all of these at once: work in every application as an input
method, run on the user's machine with nothing sent anywhere, keep Telex typing as it is, and be
open source on Linux. That combination is the gap; it was searched for, including a search aimed at
disproving it, and not found, which is not proof that it does not exist.

## What users said about v7

In the VOZ thread about v7 ([page 1](https://voz.vn/t/ky-su-tre-dung-ai-thay-doi-cach-go-tieng-viet.1099480/),
[page 3](https://voz.vn/t/ky-su-tre-dung-ai-thay-doi-cach-go-tieng-viet.1099480/page-3), May 2025),
several users did not want to change how they type ("Telex is as fixed as QWERTY") and mocked
running an AI model just to add marks. One user described the approach taken here as worth doing:
type without marks and let the method guess, as Chinese input methods do. Another called Laban
Key's guesses poor. One forum, not a survey.

## Vietnamese input methods on Linux stall

- ibus-bamboo, whose engine Ngó Sen builds on, says it "has been stalled for quite a long time and
  may not be maintained in the future" ([README](https://github.com/BambooEngine/ibus-bamboo/blob/master/README_EN.md)).
  ibus-unikey's development has also stalled ([Funtoo](https://www.funtoo.org/Package:IBus/Vietnamese)).
- Newer projects such as VMK ([fcitx5 discussion, 2026-01](https://github.com/fcitx/fcitx5/discussions/1490))
  and [Daklak](https://github.com/mozartilize/daklak-rs) work on typing mechanics (no preedit,
  Wayland, surrounding text), not on guessing marks.

A small scope that one person can maintain is the defence against the most common way these
projects end.

## Gaps

- No published accuracy for Cốc Cốc, TocKyVNKey, Laban Key or Gboard on Vietnamese marks.
- No study of how Vietnamese typists correct a wrongly guessed mark.
- How Cốc Cốc adds marks today, and whether its Linux build does.
