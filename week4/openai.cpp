#include <cstdio>
#include <cstdint>
#include <chrono>

static inline double calculate(int64_t iterations, int64_t param1, int64_t param2) noexcept {
    double result = 1.0;
    const double step = static_cast<double>(param1);
    double j1 = static_cast<double>(param1 - param2);
    double j2 = static_cast<double>(param1 + param2);

    int64_t blocks = iterations / 8;
    while (blocks--) {
        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;

        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;

        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;

        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;

        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;

        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;

        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;

        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;
    }

    int64_t rem = iterations & 7;
    while (rem--) {
        result -= 1.0 / j1; j1 += step;
        result += 1.0 / j2; j2 += step;
    }

    return result;
}

int main() {
    using clock = std::chrono::steady_clock;
    auto start = clock::now();

    double result = calculate(200000000, 4, 1) * 4.0;

    auto end = clock::now();
    double elapsed = std::chrono::duration<double>(end - start).count();

    std::printf("Result: %.12f\n", result);
    std::printf("Execution Time: %.6f seconds\n", elapsed);
    return 0;
}