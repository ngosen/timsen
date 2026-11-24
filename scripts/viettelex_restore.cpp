// Runs VietTelex's Thêm dấu on each line of stdin, for comparing it with Tim Sen on the same test
// files. Build against a checkout of github.com/ptrinh/viettelex (see docs/EXPERIMENTS.md):
//   g++ -O2 -std=c++17 -I $VT/windows/engine/include -I $VT/windows/engine/src \
//       scripts/viettelex_restore.cpp $VT/windows/engine/src/add_tones.cpp \
//       $VT/windows/engine/src/text_tools.cpp -o viettelex_restore
// usage: viettelex_restore RESOURCES_DIR < lines > restored
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

#include "viettelex/add_tones.hpp"
#include "viettelex/text_tools.hpp"

static bool read_file(const std::string& path, std::vector<uint8_t>& out) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    out.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    return true;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: viettelex_restore RESOURCES_DIR < lines\n");
        return 2;
    }
    const std::string dir = argv[1];
    std::vector<uint8_t> vnlex, enlex, vnlm;
    vtx::addtones::LanguageData data;
    // A missing model would silently fall back to word frequency, so every file is required.
    if (!read_file(dir + "/vnlexicon.bin", vnlex) || !read_file(dir + "/enlexicon.bin", enlex) ||
        !read_file(dir + "/vnlm.bin", vnlm) ||
        !data.load(vnlex.data(), vnlex.size(), enlex.data(), enlex.size(), vnlm.data(), vnlm.size()) ||
        !data.lm.ok() || data.english.size() == 0) {
        std::fprintf(stderr, "cannot load vnlexicon.bin, enlexicon.bin and vnlm.bin from %s\n", dir.c_str());
        return 1;
    }
    std::string line;
    while (std::getline(std::cin, line)) {
        const auto result = vtx::addtones::restore(vtx::text::nfc(vtx::text::fromUtf8(line)), data);
        std::cout << vtx::text::toUtf8(result.text) << '\n';
    }
    return 0;
}
