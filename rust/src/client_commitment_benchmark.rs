use ark_bls12_381::{Fr, G1Affine, G1Projective};
use ark_ec::{CurveGroup, VariableBaseMSM};
use ark_std::rand::rngs::StdRng;
use ark_std::rand::{Rng, SeedableRng};
use ark_std::UniformRand;
use std::fs::{self, File};
use std::io::Write;
use std::path::Path;
use std::time::Instant;

const BOUND_B: i64 = 4096;
const N_MAX: i64 = 100;

fn bounded_scalar(rng: &mut impl Rng, bound: i64) -> Fr {
    let v: i64 = rng.gen_range(-bound..=bound);
    if v >= 0 {
        Fr::from(v as u64)
    } else {
        -Fr::from((-v) as u64)
    }
}

fn main() {
    let dims = [10_000usize, 100_000usize, 1_000_000usize];
    let repeats = 5usize;
    let mut rng = StdRng::seed_from_u64(42);

    let results_dir = std::env::var("RIVET_RESULTS_DIR").unwrap_or_else(|_| "results".to_string());
    fs::create_dir_all(&results_dir).expect("cannot create result directory");
    let output = Path::new(&results_dir).join("client_commitment_benchmark.csv");
    let mut out = File::create(output).expect("cannot create result file");
    writeln!(out, "d,phase,trial,elapsed_ms").unwrap();

    for &d in &dims {
        eprintln!("[client commitment] generating generators for d={d} ...");
        let t_gen = Instant::now();
        let generators_proj: Vec<G1Projective> =
            (0..=d).map(|_| G1Projective::rand(&mut rng)).collect();
        let g0 = generators_proj[0];
        let gens_affine: Vec<G1Affine> = generators_proj[1..]
            .iter()
            .map(|p| p.into_affine())
            .collect();
        eprintln!(
            "[client commitment] generation took {:.2}s",
            t_gen.elapsed().as_secs_f64()
        );

        for trial in 0..repeats {
            let x: Vec<Fr> = (0..d).map(|_| bounded_scalar(&mut rng, BOUND_B)).collect();
            let rho_i = Fr::rand(&mut rng);

            let t0 = Instant::now();
            let h_x = G1Projective::msm(&gens_affine, &x).expect("MSM length mismatch");
            let c_i = h_x + g0 * rho_i;
            let elapsed_commit = t0.elapsed();
            std::hint::black_box(&c_i);

            writeln!(
                out,
                "{d},commit,{trial},{:.4}",
                elapsed_commit.as_secs_f64() * 1000.0
            )
            .unwrap();

            let g_z: Vec<Fr> = (0..d)
                .map(|_| bounded_scalar(&mut rng, BOUND_B * N_MAX))
                .collect();
            let r_total = Fr::rand(&mut rng);
            let c_a = G1Projective::rand(&mut rng);

            let t1 = Instant::now();
            let h_check = G1Projective::msm(&gens_affine, &g_z).expect("MSM length mismatch");
            let lhs = h_check + g0 * r_total;
            let _eq_check = lhs == c_a;
            let elapsed_verify = t1.elapsed();
            std::hint::black_box(_eq_check);

            writeln!(
                out,
                "{d},verify,{trial},{:.4}",
                elapsed_verify.as_secs_f64() * 1000.0
            )
            .unwrap();

            eprintln!(
                "[client commitment] d={d} trial={trial} commit={:.2}ms verify={:.2}ms",
                elapsed_commit.as_secs_f64() * 1000.0,
                elapsed_verify.as_secs_f64() * 1000.0
            );
        }
    }

    eprintln!("[client commitment] wrote results/client_commitment_benchmark.csv");
}
