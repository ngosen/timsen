<div align="center">

# Tim Sen

**Đoán dấu tiếng Việt: gõ không dấu, nhận chữ có dấu.**

[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-1f6e5c)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.88%2B-1f6e5c)](crates/timsen)
[![Python](https://img.shields.io/badge/python-3.11%2B-1f6e5c)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-%C4%91ang%20ph%C3%A1t%20tri%E1%BB%83n-c9a96e)](#tien-do)

[Bản đầu tiên](#ban-dau-tien) · [Tiến độ](#tien-do) · [Cách hoạt động](#cach-hoat-dong) ·
[Bảng & độ chính xác](#bang-va-do-chinh-xac) · [Crate Rust](#crate-rust) ·
[Đo đạc](#chay-lai-do-dac) · [Giấy phép](#giay-phep) · [English](#english)

</div>

---

Tim Sen là lõi đoán dấu đằng sau tính năng Đoán dấu của bộ gõ
[Ngó Sen](https://github.com/ngosen/ngosen) trên Linux: gõ `toi da go phim` không dấu, nhận
`tôi đã gõ phím`. *Tim sen* là phần mầm xanh bên trong hạt sen.

Repository này chứa mã nguồn nghiên cứu dùng để huấn luyện và đo đạc mô hình (`research/`), cùng
crate Rust phụ trách thêm dấu ngay khi gõ (`crates/timsen`).

<a id="muc-luc"></a>

## 📑 Mục lục

- [✨ Bản đầu tiên](#ban-dau-tien)
- [🚦 Tiến độ hiện tại](#tien-do)
- [💡 Cách hoạt động](#cach-hoat-dong)
- [📊 Bảng và độ chính xác](#bang-va-do-chinh-xac)
- [🦀 Crate Rust](#crate-rust)
- [🔬 Tự chạy lại đo đạc](#chay-lai-do-dac)
- [🔒 Quyền riêng tư](#quyen-rieng-tu)
- [📁 Cấu trúc repository](#cau-truc-repo)
- [🤝 Đóng góp](#dong-gop)
- [🏛️ Giấy phép & ghi công](#giay-phep)
- [English](#english)

<a id="ban-dau-tien"></a>

## ✨ Bản đầu tiên

Những gì người dùng Ngó Sen trên Linux sẽ có:

- **Thêm dấu ngay khi gõ, trong mọi ứng dụng:** gõ không dấu, gõ Telex như thường lệ, hoặc gõ
  xen kẽ. Vài từ cuối được thêm dấu ngay khi gõ và vẫn có thể thay đổi. Nhấn `Tab` để đổi từ
  được đoán hoặc `Esc` để giữ nguyên chữ đã gõ.
- **Từ điển cá nhân:** tự học từ những từ gõ có sẵn dấu và từ những lần sửa dấu đoán, chỉ lưu
  trên máy của người dùng.
- **Sửa âm tiết không tồn tại (`khogn` → `không`):** chỉ sửa khi chắc chắn, tắt sẵn theo mặc định.

Những gì chưa có ở bản đầu tiên:

- **Chỉ tiếng Việt chuẩn:** hỗ trợ trò chuyện khi viết đủ từ. Các từ viết tắt phổ biến (`ko`,
  `dc`) giữ nguyên như gõ. Lối viết thân mật và chính tả theo vùng miền (`lun`, `dị` thay cho
  `vậy`, `gòi`) sẽ làm sau.
- **Không gợi ý từ tiếp theo:** n-gram âm tiết sai quá thường xuyên khi gợi ý từ kế tiếp (độ phủ
  top-3 chỉ đạt 27–34% trên các kho văn bản và 14–15% trên trò chuyện), và việc gợi ý đã được
  chứng minh là làm chậm tốc độ gõ ([`docs/PRIOR_WORK.md`](docs/PRIOR_WORK.md)).
- **Không gạch chân kiểm tra chính tả:** chưa gạch chân những từ không phù hợp với ngữ cảnh.
- **Tạm thời chỉ hỗ trợ Linux:** macOS và Windows phải chờ đến khi có máy để thử gõ trên đó.

Hiện chưa phát hành gì: crate chưa có trên crates.io, bảng nhỏ mới là bản phát hành nháp, Ngó Sen
chưa có tính năng này, và chưa có C API.

<a id="tien-do"></a>

## 🚦 Tiến độ hiện tại

Tiến độ từng bước theo [`docs/PLAN.md`](docs/PLAN.md):

- **Bước 1 · Đóng gói bảng dữ liệu (Đã xong):** định dạng bảng nhị phân version 2 được ghi bởi
  `research.table` với các n-gram chọn lọc từ `research.prune --bytes`. Cả hai bảng nhỏ (22,65 MB,
  mặc định) và lớn (130,96 MB) đều đã được đo đạc trên trò chuyện, Wikipedia, phụ đề và văn bản
  diễn đàn ([`docs/TABLES.md`](docs/TABLES.md)).
- **Bước 2 · Thêm dấu cả đoạn trong Rust (Đã xong):** crate `timsen` (`crates/timsen`) đọc bảng
  `.timsen` và khôi phục các đoạn âm tiết không dấu khớp chính xác kết quả của `research.model`,
  giữ nguyên chữ hoa/thường và hỗ trợ cả kiểu đặt dấu thanh cũ lẫn mới.
- **Bước 3 · Thêm dấu ngay khi gõ (Đã xong):** `Typing` trả về cách viết tốt nhất sau mỗi âm tiết
  trong vòng chưa tới 2 ms ở p99. `Typing::choices` cung cấp ba cách viết hàng đầu kèm điểm tin
  cậy; các từ được đánh dấu chắc chắn (độ tin cậy ≥ 0,9) đoán đúng 97–98% số lần. Các âm tiết gõ
  có dấu sẽ định hướng việc đoán từ cho các từ lân cận, và `push_either` cân giữa cách bộ gõ
  diễn giải và chữ gõ thô (`tét` hay `test`).
- **Bước 4 · Từ điển cá nhân (Đã xong):** `Personal` trong crate chỉ học n-gram từ văn bản đã xác
  nhận (từ gõ có dấu và từ đoán đã được sửa), tránh để lỗi tự lặp lại và khắc sâu hơn. Nó bổ sung
  các âm tiết còn thiếu trong bảng; trên văn bản trò chuyện, bảng nhỏ tăng từ 90,61% lên 92,91% số
  từ đúng khi có từ điển này ([`docs/TABLES.md`](docs/TABLES.md)), với thời gian ở p99 đạt
  2,4–2,9 ms mỗi âm tiết.
- **Bước 5 · Sửa âm tiết không tồn tại (Đã xong):** `Typing::fix` thay thế âm tiết chưa biết bằng
  một âm tiết hợp lệ có khoảng cách sửa đổi là 1 khi vượt trội hơn từ đứng thứ nhì ít nhất 4 điểm
  (`FIX_MARGIN`). Được quyết định khi kết thúc từ, tính năng đoán đúng 98,0–99,5% số lần và sửa
  được 23–25% số lỗi gõ nhầm mà nó phát hiện được. Tắt sẵn theo mặc định; `Run::undo_fix` cho
  phép hủy lần sửa gần nhất, chỉ cần một phím để hoàn tác.
- **Bước 6 · Sẵn sàng cho bộ gõ (Đã xong):** tệp bảng được đọc hoàn toàn vào bộ nhớ khi mở (không
  dùng `memmap2`). Crate nhắm tới bản Rust tối thiểu là 1.88. `Dictionary` cung cấp khả năng cô
  lập snapshot giữa các trường nhập để các đoạn gõ không bao giờ bị lẫn số đếm. Cơ chế lưu tệp
  nguyên tử (atomic) bảo vệ từ điển cá nhân không bị hỏng. `Run` tạo các struct `Change` theo lô,
  báo lại chữ cũ và mới trước khi xóa. Giới hạn mỗi đoạn ở 200 âm tiết (`MAX_RUN`). Đã qua bài
  thử phá (dữ liệu rác, tệp hỏng, gọi sai thứ tự) và bài kiểm tra tích hợp trong lõi Ngó Sen
  (19/19 và 139/139 bài kiểm tra).
- **Bước 7 · Dùng hằng ngày trong Ngó Sen (Tiếp theo):** đã chuẩn bị sẵn trong một bản sao cục
  bộ, bản thân Ngó Sen chưa sửa đổi. Những việc còn lại cần làm: các lệnh gọi để mở bảng và từ
  điển cá nhân dùng chung, áp dụng thay đổi sau mỗi phím, hoàn tác sửa lỗi bằng Backspace, và tuỳ
  chọn Đoán dấu, tắt sẵn theo mặc định. Sau đó việc gõ phím hằng ngày sẽ quyết định nên điền sẵn
  dấu hay chỉ gợi ý dấu.

<a id="cach-hoat-dong"></a>

## 💡 Cách hoạt động

- **Mô hình ngôn ngữ:** 3-gram âm tiết với stupid backoff (hệ số 0,4) và mức phạt backoff phần dư
  (`LEFTOVER = 0.5`), phạt nặng hơn khi phải lùi về ngữ cảnh thấp hơn từ những ngữ cảnh mà bảng
  gần như giữ trọn vẹn.
- **Từ ứng viên:** với mỗi âm tiết gõ vào, bảng liệt kê mọi cách viết có dấu từng gặp
  (`go` → `gõ`, `gỗ`, `gỡ`, …).
- **Tìm kiếm:** thuật toán tìm kiếm Viterbi chọn tổ hợp các cách viết có chuỗi xuất hiện thường
  xuyên nhất. Mỗi âm tiết mới thêm vào một bước, do đó cách viết tốt nhất tính đến hiện tại luôn
  sẵn sàng sau từng phím; các từ cách 3 âm tiết trở về trước gần như đã được chốt cố định.
- **Neo ngữ cảnh:** các từ được gõ sẵn dấu rõ ràng được giữ nguyên như gõ và đóng vai trò như các
  mốc neo ngữ cảnh cố định giúp định hướng đoán từ cho các từ liền kề (tăng độ chính xác của từ
  lân cận thêm 0,7–1,4 điểm phần trăm).
- **Từ điển cá nhân:** cộng thêm số đếm 2-gram và 3-gram âm tiết từ văn bản đã xác nhận. Trọng
  số động (`min(3000, table total / tokens learned)`) giảm dần khi từ điển lớn lên, giúp số đếm
  của người dùng không lấn át số liệu của bảng.

<a id="bang-va-do-chinh-xac"></a>

## 📊 Bảng và độ chính xác

Hai bảng đều dùng chung định dạng nhị phân và hoạt động cùng một từ điển cá nhân:

| Bộ kiểm tra | Bảng nhỏ (mặc định) | Bảng lớn |
| :--- | :--- | :--- |
| Kích thước tệp | 22,65 MB | 130,96 MB |
| Trò chuyện + từ điển cá nhân | 92,91% | 92,78% |
| Trò chuyện | 90,61% | 90,65% |
| Wikipedia | 96,03% | 97,15% |
| Phụ đề | 95,73% | 96,59% |
| Diễn đàn | 93,26% | 94,30% |

Mọi số liệu đều lấy từ mục "Forum pages from every FineWeb-2 file" trong
[`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md):

- **Bộ kiểm tra:** `wiki` (4.000 câu, 73.604 từ), `subs` (4.000 câu, 31.845 từ) và `forum` (4.000
  câu, 92.220 từ) là các tệp giữ riêng, không bao giờ dùng để huấn luyện. `chat` gồm 2.604 câu lấy từ
  tin nhắn của một người viết, nên kết quả có thể khác với người khác.
- **Dữ liệu huấn luyện:** cả hai bảng đều được huấn luyện trên Wikipedia, OpenSubtitles, các tệp
  diễn đàn 1–4 của FineWeb-2 và các diễn đàn công nghệ từ tệp 1–29
  (`python -m research.train MODEL.npz wiki subs forum tech`).
- **Tỉa bớt từ vựng:** cả hai bảng đều bỏ qua các từ không dấu xuất hiện dưới 1.000 lần mà cách
  viết duy nhất chỉ là chính nó (`--min-plain 1000`), giúp giữ nguyên từ tiếng Anh và lỗi gõ phím
  như khi gõ mà không tốn dung lượng bảng.
- **Lựa chọn bảng:** khi gõ trò chuyện có kèm từ điển cá nhân, bảng nhỏ đạt kết quả ngang ngửa
  bảng lớn (92,91% so với 92,78%). Với văn bản biên tập chỉn chu, bảng lớn đoán đúng hơn khoảng
  1 từ trên 100 từ (96,03% so với 97,15% trên Wikipedia). Bảng nhỏ phát hành trước và là mặc
  định; bảng lớn là tuỳ chọn cho người dùng chủ yếu soạn thảo các văn bản dài đã qua biên tập.
- **Mức chiếm dụng bộ nhớ:** tệp bảng được đọc toàn bộ vào bộ nhớ khi mở (~40 ms), bảng nhỏ chiếm
  khoảng 31 MB RAM sau khi đã gõ qua.

<a id="crate-rust"></a>

## 🦀 Crate Rust

Crate Rust nằm tại [`crates/timsen`](crates/timsen). Crate yêu cầu Rust 1.88 trở lên (edition 2024).
Crate hiện chưa được phát hành trên crates.io; hãy khai báo phụ thuộc qua đường dẫn cục bộ (path)
hoặc kho git.

### Thêm dấu cho cả đoạn

Để thêm dấu cho một lát cắt (slice) các từ không dấu cùng lúc:

```rust
use timsen::{Table, ToneStyle};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Open the small binary table (22.65 MB)
    let table = Table::open("small.timsen")?;

    // Restore unaccented syllables
    let words = ["toi", "da", "go", "phim"];
    let restored = table.restore(&words, ToneStyle::New);
    assert_eq!(restored.join(" "), "tôi đã gõ phím");

    Ok(())
}
```

### Gõ tương tác kết hợp học từ điển cá nhân

Dành cho các bộ gõ cần xử lý từng phím gõ và số đếm của từ điển cá nhân:

```rust
use std::sync::Arc;
use timsen::{Dictionary, Table, ToneStyle};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let table = Arc::new(Table::open("small.timsen")?);
    let mut dict = Dictionary::new(table);

    // Learn from a run known to be correct (typed with marks or confirmed)
    dict.learn(&[Some("tôi"), Some("đã"), Some("gõ"), Some("phím")]);

    // Start a typing session for an input field
    let mut typing = dict.typing();
    for syllable in ["toi", "da", "go", "phim"] {
        typing.push(syllable);
    }

    let guess = typing.finish(ToneStyle::New);
    assert_eq!(guess.join(" "), "tôi đã gõ phím");

    Ok(())
}
```

<a id="chay-lai-do-dac"></a>

## 🔬 Tự chạy lại đo đạc

Yêu cầu Python 3.11 trở lên. Dữ liệu được lưu tại `TIMSEN_DIR` (mặc định là `/tmp/timsen`); dung
lượng cần khoảng vài GB:

```bash
pip install -e '.[dev]'
python -m research.fetch_wiki                 # Wikipedia, CC BY-SA
python -m research.fetch_subs                 # OpenSubtitles, counts ship with attribution
python -m research.fetch_fineweb forum 1      # forum pages from FineWeb-2 file 1 (repeat for 2-4)
python -m research.fetch_fineweb tech 1       # technology forums from file 1 (repeat for 2-29)
python -m research.train /tmp/timsen/models/wsft.npz wiki subs forum tech
python -m research.evaluate /tmp/timsen/models/wsft.npz \
    /tmp/timsen/test/wiki /tmp/timsen/test/forum
```

Để tạo các bảng nhỏ và lớn dùng cho phát hành:

```bash
python -m research.prune /tmp/timsen/models/wsft.npz small.timsen --bytes 22650896 --min-plain 1000
python -m research.prune /tmp/timsen/models/wsft.npz large.timsen --bytes 130958840 --min-plain 1000
```

Để đo đạc trên chính văn bản của bạn, hãy đặt các tin nhắn vào một tệp văn bản (mỗi dòng một tin)
rồi chạy:

```bash
python -m research.chat_testset FILE
```

Bộ kiểm tra tạo ra chỉ nằm trên máy của bạn. Giấy phép của các kho văn bản được liệt kê trong
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

<a id="quyen-rieng-tu"></a>

## 🔒 Quyền riêng tư

- **Hoàn toàn trên thiết bị:** mọi tính toán đều diễn ra cục bộ trên máy tính của người dùng. Phím
  gõ, văn bản và số đếm n-gram không bao giờ rời khỏi máy.
- **Lưu từ điển cục bộ:** từ điển cá nhân được lưu trong một tệp văn bản duy nhất mà chỉ người dùng
  mới có quyền đọc.
- **Ô nhập riêng tư:** không đoán hay học bất cứ điều gì trong ô mật khẩu và các ô riêng tư khác;
  bộ gõ không gọi tới crate ở những ô này.
- **Đánh giá cục bộ:** bộ kiểm tra được tạo từ tin nhắn của bạn bằng `research.chat_testset` chỉ
  nằm trên máy. Crate không gửi bất kỳ dữ liệu nào; kế hoạch dự kiến sẽ có lệnh "measure on my
  text" mà người dùng có thể chủ động gửi điểm số nếu muốn ([`docs/PLAN.md`](docs/PLAN.md), "From
  users").
- **Không đưa văn bản riêng tư vào git:** tuân thủ theo [`AGENTS.md`](AGENTS.md), văn bản riêng tư
  không bao giờ được commit hoặc trích dẫn trong tài liệu, pull request hay mã nguồn.

<a id="cau-truc-repo"></a>

## 📁 Cấu trúc repository

- [`crates/timsen`](crates/timsen): thư viện Rust cài đặt việc tải bảng, thêm dấu trong lúc gõ, từ
  điển cá nhân và phần báo thay đổi khi một từ kết thúc.
- `research/`: các script Python để thu thập kho văn bản, đếm n-gram, tỉa bảng, đánh giá và tạo bộ
  kiểm tra.
- `docs/`: tài liệu kỹ thuật và ghi chép của dự án:
  - [`docs/PLAN.md`](docs/PLAN.md): các bước triển khai và trạng thái từng mốc.
  - [`docs/TABLES.md`](docs/TABLES.md): benchmark kích thước bảng và so sánh độ chính xác.
  - [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md): nhật ký thực nghiệm ghi lại mọi giả thuyết đã
    thử.
  - [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md): nguồn gốc các kho văn bản, điều khoản giấy phép
    và các bộ lọc.
  - [`docs/PRIOR_WORK.md`](docs/PRIOR_WORK.md): khảo sát tài liệu nghiên cứu về gõ dự đoán và thêm
    dấu.
- `tests/`: các bài kiểm tra cho mã nghiên cứu (`python -m pytest`). Các bài kiểm tra riêng của
  crate, bao gồm việc đối chiếu với mô hình Python trên bảng fixture, nằm tại `crates/timsen/tests`.

<a id="dong-gop"></a>

## 🤝 Đóng góp

Xem [`AGENTS.md`](AGENTS.md) để biết hướng dẫn đóng góp:

- **Mọi thay đổi:** đều qua pull request vào `main` và phải vượt qua các bước kiểm tra CI.
- **Đo lường:** phải có dự đoán được ghi vào [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) trước khi
  chạy thực nghiệm.
- **Văn bản riêng tư:** tuyệt đối không được đưa vào repository.
- **Chỉ dùng tiếng Anh:** cho định danh, chú thích trong mã, commit message, mô tả PR và tài liệu
  (tệp README này là ngoại lệ).

<a id="giay-phep"></a>

## 🏛️ Giấy phép & ghi công

Mã nguồn được phát hành theo giấy phép GPL-3.0-or-later ([`LICENSE`](LICENSE)).

Các bảng số đếm phát hành tuân theo giấy phép của kho văn bản tương ứng
([`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)):

- **Wikipedia:** CC BY-SA 4.0; bảng phát hành theo giấy phép CC BY-SA 4.0.
- **FineWeb-2:** ODC-By 1.0, kèm theo điều khoản sử dụng của Common Crawl.
- **OpenSubtitles:** (<http://www.opensubtitles.org/>, qua [OPUS](https://opus.nlpl.eu/);
  P. Lison and J. Tiedemann, 2016, "OpenSubtitles2016: Extracting Large Parallel Corpora from Movie
  and TV Subtitles", LREC 2016). Không có giấy phép chính thức; bản phát hành chỉ gửi kèm số đếm,
  không bao giờ chứa văn bản.

<a id="english"></a>

## English

Tim Sen is the diacritic guesser behind the Đoán dấu feature of the
[Ngó Sen](https://github.com/ngosen/ngosen) input method on Linux: type `toi da go phim` without
marks, get `tôi đã gõ phím`. *Tim sen* is the green heart inside a lotus seed. This repository
holds the research code that trains and measures the model (`research/`) and the Rust crate that
restores marks while typing (`crates/timsen`). Nothing is released yet: the crate is not on
crates.io, the small table is a draft release, Ngó Sen does not ship the feature, and there is no C
API.

The plan, measurements and corpus licences are in English under `docs/`. The code is licensed under
GPL-3.0-or-later; tables follow their corpora's licences. The rest of this page is in Vietnamese.
