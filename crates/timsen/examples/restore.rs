//! Restores one run per input line: `cargo run --release --example restore TABLE [--old] < runs`.

use std::io::{BufRead, Write};

use timsen::{Table, ToneStyle};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let path = args.first().ok_or("usage: restore TABLE [--old] < runs")?;
    let style = if args.iter().any(|a| a == "--old") {
        ToneStyle::Old
    } else {
        ToneStyle::New
    };
    let table = Table::open(path)?;
    let mut out = std::io::BufWriter::new(std::io::stdout().lock());
    for line in std::io::stdin().lock().lines() {
        let line = line?;
        let words: Vec<&str> = line.split_whitespace().collect();
        writeln!(out, "{}", table.restore(&words, style).join(" "))?;
    }
    Ok(())
}
