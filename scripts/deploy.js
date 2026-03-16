const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying VotingContract to Sepolia...");

  const [deployer] = await ethers.getSigners();
  console.log("Deployer:", deployer.address);

  const candidateIds = [
    ethers.encodeBytes32String("C001"),
    ethers.encodeBytes32String("C002"),
    ethers.encodeBytes32String("C003"),
  ];

  const candidateNames = ["Priya Anand", "Rahul Mehta", "Sunita Rao"];

  const VotingContract = await ethers.getContractFactory("VotingContract");
  const contract = await VotingContract.deploy(candidateIds, candidateNames);
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("VotingContract deployed at:", address);

  const deployInfo = {
    contractAddress: address,
    network: "sepolia",
    deployedAt: new Date().toISOString(),
  };

  const outPath = path.join(__dirname, "backend", "contract_address.json");
  fs.writeFileSync(outPath, JSON.stringify(deployInfo, null, 2));
  console.log("Address saved to backend/contract_address.json");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});