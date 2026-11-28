//! Types keys through Ngó Sen's typing core and lists the words that nearby keys would have typed,
//! for `research.telex_typo`.
//!
//! usage: ngosen-near DICT ENGLISH KEEP [KNOWN]
//! DICT, ENGLISH and KEEP are Ngó Sen's `vietnamese.cm.dict`, `english-common.txt` and
//! `keep-words.txt`. Reads one word of Telex keys per line and prints what the core shows for it
//! when the word ends. With KNOWN, a file of unmarked forms, a tab follows and then, between
//! spaces, `word=KINDS[,KINDS]` for each other word that keys one or two slips away would have
//! typed and whose unmarked form is in KNOWN.
//!
//! A kind has one letter per slip: `n` a neighbouring key hit instead, `s` the other mark key
//! after a or o (`oo` for `ow`), `f` any other key hit instead, `t` two keys in the wrong order,
//! `r` a key hit twice, `p` an extra key beside the one before or after it, `e` any other extra
//! key, `m` one key of a doubled pair left out, `k` a mark key (`s f r x j w`) left out, `i` any
//! other key left out. Two slips are listed only when neither is one of `f`, `e`, `i`, `k`.
//!
//! `NGOSEN_NEAR_WAYS=one` stops the search at one slip, `narrow` at one slip that is none of `f`,
//! `i`, `k`, and `marks` at one slip that is neither `f` nor `i`; `f` and `i` take a key string for
//! every other letter. With `NGOSEN_NEAR_COUNT` set, the number of words searched and of key strings
//! typed for them goes to stderr at the end.
//!
//! Built outside this repository, in a crate with `ngosen-bamboo` (the `bamboo-rs` directory of
//! ngosen/ngosen) as a path dependency.

use std::cell::Cell;
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::ffi::{CStr, CString, c_char};
use std::fs::File;
use std::io::{self, BufRead, Write};
use std::os::fd::IntoRawFd;

use ngosen_bamboo as core;

/// Each row of letter keys with how far it is shifted to the right of the top row, in key widths.
const ROWS: [(&str, f32); 3] = [("qwertyuiop", 0.0), ("asdfghjkl", 0.25), ("zxcvbnm", 0.75)];

/// The keys that add a mark to the letters before them, not counting a vowel or d typed twice.
const MARK_KEYS: &[u8] = b"sfrxjw";

/// Two slips of a word this long are too many key strings to type; one slip is still tried.
const LONGEST_FOR_TWO: usize = 10;

const MARKED: [(char, &str); 7] = [
    ('a', "àáảãạăằắẳẵặâầấẩẫậ"),
    ('e', "èéẻẽẹêềếểễệ"),
    ('i', "ìíỉĩị"),
    ('o', "òóỏõọôồốổỗộơờớởỡợ"),
    ('u', "ùúủũụưừứửữự"),
    ('y', "ỳýỷỹỵ"),
    ('d', "đ"),
];

fn place(key: u8) -> Option<(usize, f32)> {
    ROWS.iter().enumerate().find_map(|(row, (keys, shift))| {
        let i = keys.bytes().position(|k| k == key)?;
        Some((row, i as f32 + shift))
    })
}

fn near(a: u8, b: u8) -> bool {
    let (Some((row_a, x_a)), Some((row_b, x_b))) = (place(a), place(b)) else {
        return false;
    };
    a != b && row_a.abs_diff(row_b) <= 1 && (x_a - x_b).abs() <= 1.0
}

/// Every key string that `typed` is one slip away from, with the kind of slip.
fn slips(typed: &[u8]) -> Vec<(Vec<u8>, char)> {
    let mut out = Vec::new();
    for i in 0..=typed.len() {
        let (before, after) = typed.split_at(i);
        let prev = before.last().copied();
        for key in b'a'..=b'z' {
            let doubled = prev == Some(key) || after.first() == Some(&key);
            let kind = match () {
                _ if doubled => 'm',
                _ if MARK_KEYS.contains(&key) => 'k',
                _ => 'i',
            };
            out.push(([before, &[key], after].concat(), kind));
        }
        let Some((&here, rest)) = after.split_first() else {
            continue;
        };
        let next = rest.first().copied();
        // After a or o, the letter again and w each add a mark, and one is typed for the other.
        let shape = |key: u8| {
            prev.is_some_and(|p| b"ao".contains(&p) && [here, key].contains(&p) && [here, key].contains(&b'w'))
        };
        for key in (b'a'..=b'z').filter(|&k| k != here) {
            let kind = match () {
                _ if shape(key) => 's',
                _ if near(key, here) => 'n',
                _ => 'f',
            };
            out.push(([before, &[key], rest].concat(), kind));
        }
        let beside = |k: Option<u8>| k.is_some_and(|k| near(k, here));
        let extra = match () {
            _ if prev == Some(here) || next == Some(here) => 'r',
            _ if beside(prev) || beside(next) => 'p',
            _ => 'e',
        };
        out.push(([before, rest].concat(), extra));
        if let Some(next) = next.filter(|&n| n != here) {
            out.push(([before, &[next, here], &rest[1..]].concat(), 't'));
        }
    }
    out
}

/// The key strings one or two slips away from `typed`, each with the kinds of slips that lead to it.
/// `ways` narrows the search: "one" to one slip, "narrow" to one slip that is none of `f`, `i`, `k`,
/// "marks" to one slip that is neither `f` nor `i`.
fn nearby(typed: &[u8], ways: &str) -> HashMap<Vec<u8>, BTreeSet<String>> {
    let cheap = |kind: char| "nstrpm".contains(kind);
    let mut out: HashMap<Vec<u8>, BTreeSet<String>> = HashMap::new();
    for (keys, kind) in slips(typed) {
        if (ways == "narrow" && "fik".contains(kind)) || (ways == "marks" && "fi".contains(kind)) {
            continue;
        }
        if ways == "all" && cheap(kind) && typed.len() <= LONGEST_FOR_TWO {
            for (keys, second) in slips(&keys) {
                if cheap(second) {
                    let mut kinds = [kind, second];
                    kinds.sort_unstable();
                    out.entry(keys).or_default().insert(kinds.iter().collect());
                }
            }
        }
        out.entry(keys).or_default().insert(kind.to_string());
    }
    out.remove(typed);
    out
}

fn unmarked(word: &str) -> String {
    let plain = |c: char| MARKED.iter().find(|(_, marked)| marked.contains(c)).map_or(c, |m| m.0);
    word.chars().map(plain).collect()
}

fn take(text: *mut c_char) -> String {
    if text.is_null() {
        return String::new();
    }
    // SAFETY: the core returns a NUL-terminated string allocated with malloc, owned by the caller.
    unsafe {
        let owned = CStr::from_ptr(text).to_string_lossy().into_owned();
        libc::free(text.cast());
        owned
    }
}

struct Core {
    engine: usize,
    ways: String,
    typed: Cell<(u64, u64)>,
}

impl Core {
    /// An engine set up as Ngó Sen sets one up with its default settings, Telex.
    fn new(dict: &str, english: &str, keep: &str) -> io::Result<Core> {
        let fd = |path: &str| File::open(path).map(|f| f.into_raw_fd() as usize);
        let name = CString::new("Telex").unwrap();
        let charset = CString::new("Unicode").unwrap();
        let option = core::EngineOption {
            auto_non_vn_restore: true,
            dd_free_style: true,
            macro_enabled: false,
            auto_capitalize_macro: false,
            spell_check_with_dicts: true,
            output_charset: charset.as_ptr(),
            modern_style: true,
            free_marking: true,
            w2u: 1,
            bracket_transform: 0,
            time_format: std::ptr::null(),
            date_format: std::ptr::null(),
            teencode: false,
        };
        let (dict, english, keep) = (fd(dict)?, fd(english)?, fd(keep)?);
        // SAFETY: the strings and the option outlive the calls, and the core takes over each fd.
        let engine = unsafe {
            let macros = core::NewMacroTable(std::ptr::null());
            let engine = core::NewEngine(name.as_ptr(), core::NewDictionary(dict), macros);
            core::EngineSetOption(engine, &option);
            engine
        };
        core::EngineSetEnglishWords(engine, core::NewWordList(english));
        core::EngineSetKeepGuard(engine, core::NewWordList(keep));
        let ways = std::env::var("NGOSEN_NEAR_WAYS").unwrap_or_else(|_| "all".to_string());
        Ok(Core {
            engine,
            ways,
            typed: Cell::new((0, 0)),
        })
    }

    /// What the field holds after these keys and a space, lowercased.
    fn shown(&self, keys: &[u8]) -> String {
        core::ResetEngine(self.engine);
        take(core::EnginePullCommit(self.engine));
        for &key in keys.iter().chain(b" ") {
            core::EngineProcessKeyEvent(self.engine, u32::from(key), 0);
        }
        let mut text = take(core::EnginePullCommit(self.engine));
        if text.is_empty() {
            core::EngineCommitPreedit(self.engine);
            text = take(core::EnginePullCommit(self.engine));
        }
        text.trim_end().to_lowercase()
    }

    fn words_nearby(&self, typed: &[u8], shown: &str, known: &HashSet<String>) -> String {
        let mut words: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        let nearby = nearby(typed, &self.ways);
        let (words_searched, strings) = self.typed.get();
        self.typed.set((words_searched + 1, strings + nearby.len() as u64));
        for (keys, kinds) in nearby {
            let word = self.shown(&keys);
            if word != shown && known.contains(&unmarked(&word)) {
                words.entry(word).or_default().extend(kinds);
            }
        }
        let item = |(word, kinds): (String, BTreeSet<String>)| {
            format!("{word}={}", kinds.into_iter().collect::<Vec<_>>().join(","))
        };
        words.into_iter().map(item).collect::<Vec<_>>().join(" ")
    }
}

fn main() -> io::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if !(3..=4).contains(&args.len()) {
        eprintln!("usage: ngosen-near DICT ENGLISH KEEP [KNOWN]");
        std::process::exit(2);
    }
    let core = Core::new(&args[0], &args[1], &args[2])?;
    let known: Option<HashSet<String>> = match args.get(3) {
        Some(path) => Some(io::read_to_string(File::open(path)?)?.lines().map(str::to_string).collect()),
        None => None,
    };
    let mut out = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line?;
        let typed = line.trim().as_bytes();
        let shown = core.shown(typed);
        match &known {
            Some(known) if typed.iter().all(u8::is_ascii_lowercase) => {
                writeln!(out, "{shown}\t{}", core.words_nearby(typed, &shown, known))?;
            }
            Some(_) => writeln!(out, "{shown}\t")?,
            None => writeln!(out, "{shown}")?,
        }
    }
    if std::env::var_os("NGOSEN_NEAR_COUNT").is_some() {
        let (words, strings) = core.typed.get();
        eprintln!("{words} words searched, {strings} key strings typed");
    }
    Ok(())
}
