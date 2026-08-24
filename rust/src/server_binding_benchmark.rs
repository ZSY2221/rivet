use ark_bls12_381::{Fr, G1Affine, G1Projective};
use ark_ec::{CurveGroup, VariableBaseMSM};
use ark_std::rand::rngs::StdRng;
use ark_std::rand::{Rng, SeedableRng};
use ark_std::UniformRand;
use rayon::prelude::*;
use std::env;
use std::fs::{self, File};
use std::io::Write;
use std::path::Path;
use std::time::Instant;

const BOUND_B: i64 = 4096;

fn parse_usize_list_env(name: &str, default: &[usize]) -> Vec<usize> {
    match env::var(name) {
        Ok(value) => value
            .split(',')
            .map(str::trim)
            .filter(|part| !part.is_empty())
            .map(|part| {
                part.parse::<usize>()
                    .unwrap_or_else(|_| panic!("invalid {name} entry: {part}"))
            })
            .collect(),
        Err(_) => default.to_vec(),
    }
}

fn bounded_scalar(rng: &mut impl Rng, bound: i64) -> Fr {
    let v: i64 = rng.gen_range(-bound..=bound);
    if v >= 0 {
        Fr::from(v as u64)
    } else {
        -Fr::from((-v) as u64)
    }
}

fn main() {
    let n_values = parse_usize_list_env("RIVET_SERVER_N_VALUES", &[100usize]);
    let d_values = parse_usize_list_env(
        "RIVET_SERVER_D_VALUES",
        &[10_000usize, 100_000usize, 1_000_000usize],
    );
    let repeats_override = env::var("RIVET_SERVER_REPEATS").ok().map(|value| {
        value
            .parse::<usize>()
            .unwrap_or_else(|_| panic!("invalid RIVET_SERVER_REPEATS: {value}"))
    });
    let results_dir = env::var("RIVET_RESULTS_DIR").unwrap_or_else(|_| "results".to_string());
    let out_path = env::var("RIVET_SERVER_OUT")
        .map(|path| Path::new(&path).to_path_buf())
        .unwrap_or_else(|_| Path::new(&results_dir).join("server_binding_benchmark.csv"));

    fs::create_dir_all(&results_dir).expect("cannot create result directory");
    let mut out = File::create(&out_path).expect("cannot create result file");
    writeln!(
        out,
        "n_clients,d,mode,repeat,total_elapsed_ms,throughput_msm_per_sec"
    )
    .unwrap();

    let n_threads = rayon::current_num_threads();
    eprintln!("[server binding] rayon threads = {n_threads}");

    for &d in &d_values {
        eprintln!("[server binding] generating generators for d={d} ...");
        let mut gen_rng = StdRng::seed_from_u64(1234 + d as u64);
        let gens_affine: Vec<G1Affine> = (0..d)
            .map(|_| G1Projective::rand(&mut gen_rng).into_affine())
            .collect();

        for &n in &n_values {
            let repeats = repeats_override.unwrap_or(5);

            let base_seed = 5678u64.wrapping_add(d as u64).wrapping_add(n as u64);
            let gen_client_eps = |client_idx: usize| -> Vec<Fr> {
                let mut rng = StdRng::seed_from_u64(base_seed.wrapping_add(client_idx as u64));
                (0..d).map(|_| bounded_scalar(&mut rng, BOUND_B)).collect()
            };

            for rep_idx in 0..repeats {
                let rep = rep_idx;
                let t0 = Instant::now();
                for client_idx in 0..n {
                    let eps = gen_client_eps(client_idx);
                    let h_eps = G1Projective::msm(&gens_affine, &eps).expect("MSM length mismatch");
                    std::hint::black_box(h_eps);
                }
                let elapsed_single = t0.elapsed();
                let throughput_single = n as f64 / elapsed_single.as_secs_f64();
                writeln!(
                    out,
                    "{n},{d},single_thread,{rep},{:.4},{:.4}",
                    elapsed_single.as_secs_f64() * 1000.0,
                    throughput_single
                )
                .unwrap();
                eprintln!(
                    "[server binding] N={n} d={d} rep={rep} single_thread total={:.2}ms throughput={:.2} MSM/s",
                    elapsed_single.as_secs_f64() * 1000.0,
                    throughput_single
                );

                let t1 = Instant::now();
                (0..n).into_par_iter().for_each(|client_idx| {
                    let eps = gen_client_eps(client_idx);
                    let h_eps = G1Projective::msm(&gens_affine, &eps).expect("MSM length mismatch");
                    std::hint::black_box(h_eps);
                });
                let elapsed_multi = t1.elapsed();
                let throughput_multi = n as f64 / elapsed_multi.as_secs_f64();
                writeln!(
                    out,
                    "{n},{d},multi_thread_{n_threads},{rep},{:.4},{:.4}",
                    elapsed_multi.as_secs_f64() * 1000.0,
                    throughput_multi
                )
                .unwrap();
                eprintln!(
                    "[server binding] N={n} d={d} rep={rep} multi_thread({n_threads}) total={:.2}ms throughput={:.2} MSM/s",
                    elapsed_multi.as_secs_f64() * 1000.0,
                    throughput_multi
                );

                out.flush().ok();
            }
        }
    }

    eprintln!("[server binding] wrote results/server_binding_benchmark.csv");
}
