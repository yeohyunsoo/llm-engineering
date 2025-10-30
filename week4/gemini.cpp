
#include <iostream>
#include <vector>
#include <thread>
#include <numeric>
#include <chrono>
#include <iomanip>
#include <algorithm> // For std::min

// Worker function for a thread to calculate a partial sum over a given range.
// This function is designed to be run in parallel on different chunks of the main loop.
void calculate_partial(long long start_i, long long end_i, double param1, double param2, double* result) {
    double partial_sum = 0.0;
    for (long long i = start_i; i < end_i; ++i) {
        // Use double for 'i' to ensure floating-point arithmetic, matching Python's behavior.
        double d_i = static_cast<double>(i);
        // The core calculation, identical to the Python script's logic.
        // This form is friendly to compiler auto-vectorization.
        partial_sum += 1.0 / (d_i * param1 + param2) - 1.0 / (d_i * param1 - param2);
    }
    *result = partial_sum;
}

// Calculates the result in parallel by splitting the iterations across all available hardware threads.
double calculate_parallel(long long iterations, double param1, double param2) {
    // Determine the optimal number of threads, defaulting to 1 if detection fails.
    unsigned int num_threads = std::thread::hardware_concurrency();
    if (num_threads == 0) {
        num_threads = 1;
    }

    std::vector<std::thread> threads;
    threads.reserve(num_threads);
    std::vector<double> partial_results(num_threads);

    // Divide the total iterations into chunks for each thread.
    long long chunk_size = (iterations + num_threads - 1) / num_threads;

    for (unsigned int i = 0; i < num_threads; ++i) {
        long long start = i * chunk_size + 1;
        long long end = std::min(start + chunk_size, iterations + 1);

        if (start > iterations) {
            break;
        }

        // Launch a thread to process each chunk.
        threads.emplace_back(calculate_partial, start, end, param1, param2, &partial_results[i]);
    }

    // Wait for all threads to complete their calculations.
    for (auto& t : threads) {
        t.join();
    }

    // The initial value is 1.0, to which all partial sums are added.
    // std::reduce is an efficient way to sum the elements of the vector.
    double total_sum = std::reduce(partial_results.cbegin(), partial_results.cend(), 1.0);

    return total_sum;
}

int main() {
    // Use fast I/O operations.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    const long long iterations = 200'000'000;
    const double param1 = 4.0;
    const double param2 = 1.0;

    auto start_time = std::chrono::high_resolution_clock::now();

    // The main calculation, parallelized for maximum speed.
    double result = calculate_parallel(iterations, param1, param2) * 4.0;

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> diff = end_time - start_time;

    // Print the result and execution time, matching the Python script's format.
    std::cout << "Result: " << std::fixed << std::setprecision(12) << result << '\n';
    std::cout << "Execution Time: " << std::fixed << std::setprecision(6) << diff.count() << " seconds\n";

    return 0;
}
